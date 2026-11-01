"""Stdlib unittest suite:  python -m unittest discover -s tests -v
Needs numpy and ffmpeg. Uses the mock engine and tests/fake_acestep (a stand-in for the ACE-Step API)."""
import json, os, shutil, subprocess, sys, tempfile, threading, unittest, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def run(args, home, env=None, stdin=None):
    e = {**os.environ, "MUSIC_STUDIO_HOME": str(home), "MUSIC_STUDIO_FAKE_VRAM_GB": "16", **(env or {})}
    return subprocess.run([sys.executable, *args], cwd=SCRIPTS, env=e, input=stdin, capture_output=True, text=True)


def events(res):
    return [json.loads(l) for l in res.stdout.splitlines() if l.startswith("{")]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.home = self.tmp / "ws"
        run(["msconfig.py", "init"], self.home)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sh(self, *a, **k):
        return run(list(a), self.home, **k)

    def spec(self, **kw):
        r = self.sh("msconfig.py", "plan", "--style", "lofi", "--duration", "12", "--quality", "draft",
                    "--bpm", "90", *sum([[f"--{k}", str(v)] for k, v in kw.items()], []))
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout


class TestConfig(Base):
    def test_layering_and_unset(self):
        self.sh("msconfig.py", "set", "generation.duration", "77")
        cfg = json.loads(self.sh("msconfig.py", "show", "--explain").stdout)
        self.assertEqual(cfg["config"]["generation"]["duration"], 77)
        self.sh("msconfig.py", "unset", "generation.duration")
        cfg = json.loads(self.sh("msconfig.py", "show").stdout)
        self.assertNotEqual(cfg["config"]["generation"]["duration"], 77)

    def test_tiers(self):
        import gpu
        self.assertEqual([gpu.tier_for(v) for v in (4, 8, 16, 24)], ["low", "mid", "high", "ultra"])

    def test_unknown_style_fails(self):
        self.assertEqual(self.sh("msconfig.py", "plan", "--style", "nope").returncode, 2)

    def test_user_style_overrides(self):
        d = self.home / "styles"; d.mkdir(exist_ok=True)
        (d / "mine.json").write_text(json.dumps({"id": "mine", "name": "Mine", "caption": "x, y", "bpm": [60, 70], "keys": ["C Major"]}))
        ids = [s["id"] for s in json.loads(self.sh("msconfig.py", "styles").stdout)]
        self.assertIn("mine", ids)
        self.assertIn("lofi", ids)

    def test_precedence_request_beats_preset(self):
        spec = json.loads(self.spec(variants=1))
        self.assertEqual(spec["variants"], 1)


class TestCaption(Base):
    def plan(self, *a):
        r = self.sh("msconfig.py", "plan", *a)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_description_reaches_caption(self):
        d = self.plan("--style", "from-description", "--description", "下雨天讀書用的溫暖鋼琴音樂")
        for tag in ("soft rain ambience", "warm piano"):
            self.assertIn(tag, d["caption"])

    def test_negation_removes_conflicting_style_tags(self):
        d = self.plan("--style", "lofi", "--description", "不要鼓")
        self.assertIn("no percussion", d["caption"])
        self.assertNotIn("boom bap drums", d["caption"])

    def test_longest_match_wins(self):
        d = self.plan("--style", "from-description", "--description", "電吉他")
        self.assertIn("electric guitar", d["caption"])
        self.assertNotIn("fingerpicked acoustic guitar", d["caption"])

    def test_unknown_chinese_reported_not_guessed(self):
        d = self.plan("--style", "from-description", "--description", "超酷氣氛")
        self.assertTrue(any("not understood" in w for w in d["warnings"]))

    def test_tag_cap_and_user_words_survive(self):
        d = self.plan("--style", "lofi", "--description", "下雨 咖啡廳 鋼琴 寂寞 夜晚 森林 營火", "--mood", "cozy,calm,nostalgic,hopeful")
        self.assertLessEqual(len(d["caption"].split(", ")), 14)
        self.assertLessEqual(len(d["caption"]), 512)
        self.assertIn("soft rain ambience", d["caption"])

    def test_style_instruments_shape_caption(self):
        d = self.plan("--style", "rpg-battle")
        self.assertEqual(d["instruments"]["mode"], "style")
        self.assertIn("taiko", d["instruments"]["use"])
        self.assertIn("synth-pad", d["instruments"]["avoid"])

    def test_custom_instruments_replace_style_ones(self):
        d = self.plan("--style", "rpg-battle", "--instruments", "erhu,guzheng,taiko")
        self.assertIn("erhu", d["caption"])
        self.assertIn("guzheng", d["caption"])
        self.assertIn("taiko drums", d["caption"])  # chosen and already in the style: kept, not duplicated
        self.assertNotIn("brass stabs", d["caption"])
        self.assertNotIn("strings ostinato", d["caption"])
        self.assertEqual(d["caption_parts"]["instruments"], ["erhu", "guzheng"])

    def test_avoid_instrument_strips_style_tag(self):
        d = self.plan("--style", "lofi", "--avoid-instruments", "drums")
        self.assertNotIn("boom bap drums", d["caption"])
        self.assertIn("drums", d["instruments"]["avoid"])

    def test_description_beats_style_avoid(self):
        d = self.plan("--style", "nature-piano", "--description", "合成器鋪底")
        self.assertIn("warm synth pads", d["caption"])
        self.assertTrue(any("usually avoids" in w for w in d["warnings"]))

    def test_builtin_styles_use_music_theory_not_vague_words(self):
        import msconfig
        for f in sorted((ROOT / "defaults" / "styles").glob("*.json")):
            cap = json.loads(f.read_text(encoding="utf-8"))["caption"]
            self.assertEqual(msconfig.vague_words(cap), [], f.name)

    def test_unknown_instrument_warns(self):
        d = self.plan("--style", "lofi", "--instruments", "kazoo")
        self.assertTrue(any("unknown instrument" in w for w in d["warnings"]))

    def test_war_requiem_has_no_synths(self):
        d = self.plan("--style", "war-requiem", "--description", "戰敗 犧牲 悲壯")
        for tag in ("cello melody", "French horn", "solemn sacrifice"):
            self.assertIn(tag, d["caption"])
        self.assertNotIn("synth", d["caption"].lower())

    def test_override_and_stable_key(self):
        d = self.plan("--style", "lofi", "--caption", "a, b, c")
        self.assertEqual(d["caption"], "a, b, c")
        k1 = self.plan("--style", "lofi", "--description", "x")["key"]
        k2 = self.plan("--style", "lofi", "--description", "x")["key"]
        self.assertEqual(k1, k2)

    def test_low_tier_offloads_dit_so_vae_has_room(self):
        import msconfig
        cfg, _ = msconfig.load_config(self.home)
        r = msconfig.resolve_params(cfg, "standard", tier="low")
        self.assertTrue(r["params"]["offload_dit_to_cpu"])

    def test_low_tier_offloads_dit_so_vae_has_room(self):
        import msconfig
        cfg, _ = msconfig.load_config(self.home)
        r = msconfig.resolve_params(cfg, "standard", tier="low")
        self.assertTrue(r["params"]["offload_dit_to_cpu"])
        self.assertEqual([w for w in r["warnings"] if "variants" in w], [])

    def test_tiers_follow_acestep_guidance(self):
        cfg = json.loads(self.sh("msconfig.py", "show").stdout)["config"]["hardware"]["tiers"]
        self.assertIsNone(cfg["mid"]["quantization"])
        self.assertEqual(cfg["mid"]["lm_model"], "acestep-5Hz-lm-0.6B")
        self.assertIsNone(cfg["low"]["quantization"])


class TestMockPipeline(Base):
    def generate(self, **kw):
        r = self.sh("engine.py", "generate", "--spec", "-", "--engine", "mock", stdin=self.spec(**kw))
        self.assertEqual(r.returncode, 0, r.stderr)
        res = [e for e in events(r) if e["event"] == "result"][0]
        self.assertTrue(res["ok"])
        return res

    def test_generate_and_finalize_loop(self):
        res = self.generate(workflow="game-bgm", variants=1)
        p = self.sh("postprocess.py", "run", "--take", res["id"], "--workflow", "game-bgm")
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertIn("loop", out["applied"])
        self.assertAlmostEqual(out["report"]["lufs"], -16.0, delta=0.6)
        self.assertLessEqual(out["report"]["true_peak_db"], -1.0)
        self.assertTrue(any(f.endswith(".ogg") for f in out["files"]))

    def test_every_variant_gets_an_automatic_check(self):
        res = self.generate(variants=2)
        take = json.loads(self.sh("library.py", "show", res["id"]).stdout)
        self.assertTrue(all(isinstance(v.get("qc"), list) for v in take["variants"]))

    def test_loudness_preset_overrides_workflow_target(self):
        res = self.generate(workflow="game-bgm", variants=1)
        p = self.sh("postprocess.py", "run", "--take", res["id"], "--workflow", "game-bgm", "--loudness", "video")
        self.assertEqual(p.returncode, 0, p.stderr)
        rep = json.loads(p.stdout)["report"]
        self.assertAlmostEqual(rep["lufs"], -14.0, delta=0.6)
        self.assertFalse(any("off target" in q for q in rep["qc"]), rep["qc"])
        bad = self.sh("postprocess.py", "run", "--take", res["id"], "--loudness", "loud")
        self.assertNotEqual(bad.returncode, 0)

    def test_deterministic_seed(self):
        a, b = self.generate(seed=5, variants=1), self.generate(seed=5, variants=1)
        fa = Path(a["dir"]) / a["variants"][0]["file"]; fb = Path(b["dir"]) / b["variants"][0]["file"]
        self.assertEqual(fa.read_bytes(), fb.read_bytes())

    def test_library_roundtrip(self):
        res = self.generate(variants=1)
        self.sh("library.py", "annotate", res["id"], "rating=5", "favorite=true", "tags=a,b")
        t = json.loads(self.sh("library.py", "list").stdout)[0]
        self.assertEqual((t["rating"], t["favorite"], t["tags"]), (5, True, ["a", "b"]))
        self.assertNotEqual(self.sh("library.py", "annotate", res["id"], "bogus=1").returncode, 0)
        self.sh("library.py", "trash", res["id"])
        self.assertEqual(json.loads(self.sh("library.py", "list").stdout), [])
        self.assertTrue(any((self.home / "trash").iterdir()))


class TestAceRunner(Base):
    def setUp(self):
        super().setUp()
        self.ace = self.tmp / "ace"
        shutil.copytree(ROOT / "tests" / "fake_acestep", self.ace, symlinks=False, ignore=shutil.ignore_patterns(".venv"))
        # git does not keep empty folders, so the fake checkpoints are made here (no sft: tests its fallback)
        for name in ("acestep-v15-turbo", "vae", "Qwen3-Embedding-0.6B", "acestep-5Hz-lm-1.7B"):
            (self.ace / "checkpoints" / name).mkdir(parents=True, exist_ok=True)
        py = self.ace / ".venv" / "bin"; py.mkdir(parents=True)
        (py / "python").symlink_to(sys.executable)
        self.sh("msconfig.py", "set", "ace_step_dir", str(self.ace))
        self.sh("msconfig.py", "set", "engine", "ace")

    def gen(self, env=None):
        r = self.sh("engine.py", "generate", "--spec", "-", stdin=self.spec(variants=2), env=env)
        return r, events(r)

    def test_happy_path(self):
        r, ev = self.gen()
        self.assertEqual(ev[-1]["event"], "result", r.stderr[-500:])
        self.assertTrue(ev[-1]["ok"])

    def test_lm_backend_fallback_continues(self):
        r, ev = self.gen({"FAKE_LM_FAIL_ALL": "1"})
        self.assertTrue(ev[-1].get("ok"), r.stderr[-500:])

    def test_oom_retries_with_batch_1(self):
        r, ev = self.gen({"FAKE_OOM": "1"})
        self.assertTrue(any(e["event"] == "retry" for e in ev))
        self.assertTrue(ev[-1].get("ok"))

    def test_sft_fallback_clamps_turbo_steps(self):
        r = self.sh("engine.py", "generate", "--spec", "-", stdin=self.spec(variants=1, quality="high"))
        ev = events(r)
        self.assertTrue(ev[-1].get("ok"), r.stderr[-400:])
        warns = " ".join(e.get("message", "") for e in ev if e["event"] == "warn")
        self.assertIn("not installed", warns)
        self.assertIn("8 steps", warns)

    def test_models_listing(self):
        r = self.sh("engine.py", "models")
        d = json.loads(r.stdout)
        self.assertIn("acestep-v15-turbo", d["installed"])
        self.assertIn("missing", d)

    def test_failure_reports_error_event(self):
        r, ev = self.gen({"FAKE_FAIL": "1"})
        self.assertEqual(ev[-1]["event"], "error")
        self.assertNotEqual(r.returncode, 0)


class TestInspect(unittest.TestCase):
    """The automatic check flags what a listener would notice and stays quiet on ordinary music."""
    def setUp(self):
        import numpy as np
        self.np, self.sr = np, 48000
        t = np.arange(self.sr * 20) / self.sr
        tone = 0.3 * np.sin(2 * np.pi * 220 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t))
        x = np.stack([tone, tone], 1)
        x[-self.sr * 2:] *= np.linspace(1, 0, self.sr * 2)[:, None]  # a proper fade-out
        self.x = x

    def codes(self, x, **kw):
        import postprocess
        return [i["code"] for i in postprocess.inspect_audio(x, self.sr, **kw)]

    def test_clean_music_has_no_issues(self):
        np = self.np
        drums = self.x * 0.5
        rng = np.random.default_rng(0)
        for k in range(36):  # snare-like bursts are transients, not clicks
            s0, n = int(k * self.sr * 0.5), int(self.sr * 0.15)
            drums[s0:s0 + n] += (rng.standard_normal(n) * 0.4 * np.exp(-np.arange(n) / (self.sr * 0.03)))[:, None]
        self.assertEqual(self.codes(self.x), [])
        self.assertEqual(self.codes(drums), [])

    def test_flags_each_problem(self):
        np = self.np
        click = self.x.copy(); click[self.sr * 5] += 0.5
        gap = self.x.copy(); gap[self.sr * 6:self.sr * 9] = 0
        cut = self.x[: self.sr * 10]
        self.assertEqual(self.codes(click), ["clicks"])
        self.assertEqual(self.codes(gap), ["silence"])
        self.assertEqual(self.codes(cut), ["cut_off"])
        self.assertEqual(self.codes(cut, loopable=True), [])
        self.assertIn("clipping", self.codes(np.clip(self.x * 5, -1, 1)))
        self.assertEqual(self.codes(self.x * 1e-4), ["near_silent"])
        self.assertEqual(self.codes(self.x * 0.1), ["low_volume"])

    def test_tail_silence_with_faint_noise_is_not_mid_silence(self):
        np = self.np
        rng = np.random.default_rng(1)
        tail = self.x.copy(); tail[self.sr * 16:] = 0  # music ends at 16 s, silent to 20 s
        tail[-self.sr // 3:] += (rng.standard_normal(self.sr // 3) * 3e-4)[:, None]  # ~-70 dB hiss, last 0.33 s
        tail[-self.sr // 5:] += (rng.standard_normal(self.sr // 5) * 1e-3)[:, None]  # ~-60 dB floor, last 0.2 s
        self.assertNotIn("silence", self.codes(tail))
        gap = tail.copy(); gap[self.sr * 18:self.sr * 19] = self.x[self.sr * 2:self.sr * 3]  # real music after the gap
        self.assertIn("silence", self.codes(gap))


class TestPostprocessOps(unittest.TestCase):
    def test_loop_seam_metrics_clean_for_periodic_signal(self):
        import numpy as np, postprocess
        sr = 48000; t = np.arange(sr * 16) / sr
        x = (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
        m = postprocess.seam_metrics(np.stack([x, x], 1), sr)
        self.assertLess(m["click_ratio"], 4)


class TestServer(Base):
    def setUp(self):
        super().setUp()
        os.environ["MUSIC_STUDIO_HOME"] = str(self.home)
        os.environ["MUSIC_STUDIO_FAKE_VRAM_GB"] = "16"
        import server
        self.server = server
        self.srv = server.make_server("127.0.0.1", 0)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown(); self.srv.server_close(); super().tearDown()

    def req(self, path, method="GET", body=None, token=True, host=None):
        r = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method,
                                   data=json.dumps(body).encode() if body is not None else None)
        if token: r.add_header("X-Token", self.server.TOKEN)
        if host: r.add_header("Host", host)
        try:
            with urllib.request.urlopen(r) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_security(self):
        self.assertEqual(self.req("/api/state")[0], 200)
        self.assertEqual(self.req("/api/config", "PUT", {"set": {}}, token=False)[0], 403)
        self.assertEqual(self.req("/api/state", host="evil.example")[0], 403)
        self.assertEqual(self.req("/audio/..%2F..%2Fconfig.json/x")[0], 404)
        self.assertEqual(self.req("/server.py")[0], 404)

    def test_plan_preview_endpoint(self):
        code, body = self.req("/api/plan", "POST", {"style": "from-description", "description": "下雨 鋼琴"})
        self.assertEqual(code, 200)
        d = json.loads(body)
        self.assertIn("soft rain ambience", d["spec"]["caption"])
        self.assertIn("dit_model", d["params"])
        code, body = self.req("/api/plan", "POST", {"style": "rpg-battle", "instruments": ["erhu"], "avoid_instruments": ["taiko"]})
        d = json.loads(body)["spec"]
        self.assertIn("erhu", d["caption"])
        self.assertNotIn("taiko", d["caption"])

    def test_token_injected_and_config_put(self):
        code, body = self.req("/")
        self.assertIn(self.server.TOKEN.encode(), body)
        self.assertEqual(self.req("/api/config", "PUT", {"set": {"generation.duration": 33}})[0], 200)
        cfg = json.loads(self.req("/api/config")[1])
        self.assertEqual(cfg["config"]["generation"]["duration"], 33)

    def test_bad_style_id_rejected(self):
        self.assertEqual(self.req("/api/styles/a%20b", "PUT", {"name": "x"})[0], 400)
        self.assertEqual(self.req("/api/styles/..%2Fx", "PUT", {"name": "x"})[0], 400)


class TestQueueAndWorker(Base):
    """Persistent worker + single GPU queue, against the fake ACE-Step package."""

    def setUp(self):
        super().setUp()
        self.ace = self.tmp / "ace"
        shutil.copytree(ROOT / "tests" / "fake_acestep", self.ace, ignore=shutil.ignore_patterns(".venv"))
        (self.ace / ".venv" / "bin").mkdir(parents=True)
        (self.ace / ".venv" / "bin" / "python").symlink_to(sys.executable)
        self.sh("msconfig.py", "set", "ace_step_dir", str(self.ace))
        self.sh("msconfig.py", "set", "engine", "ace")
        self.initlog = self.tmp / "init.log"
        self.env_backup = dict(os.environ)
        os.environ.update(MUSIC_STUDIO_HOME=str(self.home), MUSIC_STUDIO_FAKE_VRAM_GB="16", FAKE_INIT_LOG=str(self.initlog))
        import jobs
        self.q = jobs.JobQueue(self.home)

    def tearDown(self):
        self.q.shutdown()
        os.environ.clear(); os.environ.update(self.env_backup)
        super().tearDown()

    def submit(self, **kw):
        return self.q.submit(json.loads(self.spec(**kw)))["id"]

    def wait_for(self, jid, statuses=("done", "failed", "cancelled"), timeout=60):
        import time
        end = time.time() + timeout
        while time.time() < end:
            j = self.q.get(jid)
            if j["status"] in statuses:
                return j
            time.sleep(0.2)
        self.fail(f"job {jid} stuck: {self.q.get(jid)}")

    def test_models_stay_loaded_between_jobs(self):
        a, b = self.submit(variants=1), self.submit(variants=1)
        ja, jb = self.wait_for(a), self.wait_for(b)
        self.assertEqual((ja["status"], jb["status"]), ("done", "done"), (ja.get("error"), jb.get("error")))
        self.assertEqual(len(self.initlog.read_text().splitlines()), 1)  # loaded once, reused
        takes = json.loads(self.sh("library.py", "list").stdout)
        self.assertEqual(len(takes), 2)

    def test_model_change_reloads(self):
        self.wait_for(self.submit(variants=1))
        self.sh("msconfig.py", "set", "hardware.tiers.high.quantization", "int8_weight_only")
        self.wait_for(self.submit(variants=1))
        self.assertEqual(len(self.initlog.read_text().splitlines()), 2)

    def test_cancel_running_job_leaves_no_take(self):
        os.environ["FAKE_SLOW"] = "6"
        jid = self.submit(variants=1)
        self.wait_for(jid, statuses=("running",), timeout=20)
        import time; time.sleep(1.5)
        self.q.cancel(jid)
        j = self.wait_for(jid)
        self.assertEqual(j["status"], "cancelled")
        self.assertEqual(json.loads(self.sh("library.py", "list").stdout), [])
        self.assertTrue(any((self.home / "trash").iterdir()))
        os.environ.pop("FAKE_SLOW")
        self.assertEqual(self.wait_for(self.submit(variants=1))["status"], "done")  # fresh worker after the kill

    def test_failed_job_reports_error_and_no_take(self):
        os.environ["FAKE_FAIL"] = "1"
        j = self.wait_for(self.submit(variants=1))
        self.assertEqual(j["status"], "failed")
        self.assertIn("exploded", j["error"]["message"])
        self.assertEqual(json.loads(self.sh("library.py", "list").stdout), [])

    def test_cancel_queued_and_persisted_history(self):
        os.environ["FAKE_SLOW"] = "3"
        a, b = self.submit(variants=1), self.submit(variants=1)
        self.q.cancel(b)
        self.assertEqual(self.wait_for(b)["status"], "cancelled")
        self.wait_for(a)
        saved = json.loads((self.home / "jobs.json").read_text())
        self.assertEqual({j["id"]: j["status"] for j in saved["jobs"]}, {a: "done", b: "cancelled"})

    def test_orphan_folders_swept(self):
        import pipeline, time
        d = self.home / "output" / "20260101-000000-old"
        d.mkdir(parents=True)
        (d / "spec.json").write_text("{}")
        os.utime(d, (time.time() - 600, time.time() - 600))
        self.assertEqual(pipeline.sweep_orphans(self.home), [d.name])
        self.assertFalse(d.exists())


class TestClient(Base):
    def test_msclient_starts_server_and_generates(self):
        import signal
        try:
            r = self.sh("msclient.py", "generate", "--spec", "-", "--engine", "mock", stdin=self.spec(variants=1))
            ev = events(r)
            self.assertEqual(ev[-1]["event"], "result", r.stdout[-800:] + r.stderr[-800:])
            self.assertTrue(Path(ev[-1]["dir"]).is_dir())
            st = self.sh("msclient.py", "status")
            self.assertIn('"done"', st.stdout)
        finally:
            info = json.loads((self.home / "server.json").read_text()) if (self.home / "server.json").exists() else None
            if info:
                os.kill(info["pid"], signal.SIGTERM)


if __name__ == "__main__":
    unittest.main()

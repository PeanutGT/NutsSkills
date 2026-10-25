import os


class LLMHandler:
    def initialize(self, checkpoint_dir, lm_model_path, backend, device):
        if backend == "pt" and os.environ.get("FAKE_LM_FAIL_PT"):
            return ("pt backend unavailable", False)
        if os.environ.get("FAKE_LM_FAIL_ALL"):
            raise RuntimeError("no LM backend works")
        self.backend = backend
        return ("ready", True)

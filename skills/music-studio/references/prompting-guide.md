# Writing captions for instrumental music (ACE-Step)

Read this when turning a person's description into the `caption` of a track spec.
The caption is the single biggest lever on how the result sounds.

## Shape of a good caption

A comma-separated list of short, concrete tags, roughly in this order. Most captions need 6-12 tags:

1. **Genre / style** - `lo-fi hip hop`, `epic orchestral`, `chiptune`, `dark ambient`
2. **`instrumental`** - say it even though the engine's instrumental flag is on; it reinforces it
3. **Lead instruments** - `warm Rhodes piano`, `fingerpicked guitar`, `taiko drums`
4. **Rhythm / energy** - `laid-back boom bap drums`, `driving ostinato`, `no percussion`
5. **Mood / character** - `nostalgic`, `tense`, `spacious`
6. **Production / space** - `tape saturation`, `dry and intimate`, `big hall reverb`
7. **Use-case colour (optional)** - `casual puzzle game`, `night drive`, `film score`

Tempo and key go in the `bpm` and `key` fields of the spec, not in the caption.

## Rules of thumb

These come from how text-to-music models generally behave, not from a spec - treat them as defaults to test, not laws.

- **Concrete beats poetic.** `soft piano, marimba, pizzicato strings` steers better than `a feeling of morning light`.
- **Write the caption in English** even when the person writes Chinese. Translate the intent; keep their proper nouns out.
- **Fewer conflicting ideas.** `calm, aggressive, epic` pulls three ways. If a request is contradictory, ask which wins, or put the lesser one in as a hint (`slightly tense`).
- **Say what to leave out by what you include.** There is no negative caption: to avoid drums write `no percussion`, to avoid vocals keep `instrumental` and never add vocal words.
- **Loops want boring structure.** For looping game music add `steady`, `repetitive`, and avoid `build`, `crescendo`, `intro`, `outro`. For scene music do the opposite and describe the arc: `slow build, swelling, resolves gently`.
- **Do not name real artists, songs, games or films.** It is unreliable and it is the wrong place to borrow from. Describe what you hear instead (`80s analog synth arpeggios, gated reverb snare`).

## Iterating

- Change **one** thing per round (one tag, or the BPM, or the key). Otherwise nobody learns what helped.
- Keep the seed of a variant you liked and vary one tag. With the same seed a small caption change often stays recognisably close to the original, but that is a tendency, not a guarantee.
- Generate 2-3 variants per round; picking is cheaper than perfecting a prompt.
- If everything sounds generic, add specific instruments and a production tag before adding adjectives.

## Examples

| Request | Caption |
|---|---|
| "sleepy rainy-day study music" | `lo-fi hip hop, instrumental, mellow, warm Rhodes piano, soft rain ambience, laid-back drums, dusty vinyl crackle, cozy, relaxing` |
| "tense music for a heist scene, 40 s" | `cinematic suspense, instrumental, low pulsing synth, ticking percussion, dissonant strings, rising tension, thriller underscore` |
| "village theme for my RPG, must loop" | `fantasy RPG village theme, instrumental, acoustic guitar, flute, harp, warm, pastoral, steady, repetitive` |
| "boss fight, final phase" | `epic orchestral battle music, instrumental, driving strings ostinato, brass stabs, taiko drums, intense, fast, dramatic, heavy` |

## Using the style library

`msconfig.py plan --style S --mood a,b --caption-extra "..."` already assembles style tags + mood tags + your extras and removes duplicates. Start from the nearest style and add 1-3 extra tags rather than writing a caption from scratch.

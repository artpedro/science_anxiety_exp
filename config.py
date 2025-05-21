from pathlib import Path

class Config:
    # ── Timing parameters (seconds) ─────────────────────────────
    PRE_QUESTION_WAIT      = 0.5
    NOISE_TO_QUESTION_WAIT = 0.5
    INTERACTIVE_DURATION   = 0.5
    POST_QUESTION_WAIT     = 0.5
    INPUT_DURATION         = 0.5

    # ── File-system layout ─────────────────────────────────────
    BASE_DATA_DIR         = Path("./patients")
    GLOBAL_QUESTIONS_DIR  = Path("./data/questions")  # parent for science_questions
    GLOBAL_METADATA_CSV   = Path("./data/metadata.csv")
    SOUND_DIR             = Path("./data/sounds")
    EASY_AUDIO            = SOUND_DIR / "bell.wav"
    HARD_AUDIO            = SOUND_DIR / "bassattack.wav"
    ANSWER_NOW_AUDIO      = SOUND_DIR / "say.wav"
    SUCCESS_AUDIO         = SOUND_DIR / "success.wav"
    WRONG_AUDIO           = SOUND_DIR / "wrong.wav"

    # ── Display settings ───────────────────────────────────────
    FULLSCREEN            = False
    WINDOW_SIZE           = (900, 500)
    WINDOW_COLOR          = "gray"           # gray background for cross

    # ── Visual-stim text settings ─────────────────────────────
    STIM_TEXT            = "+"              # cross shape
    STIM_COLOR           = "black"          # black cross on gray
    STIM_HEIGHT          = 0.2
    START_TEXT           = "Press SPACE to start the experiment"
    START_TEXT_HEIGHT    = 0.1

    # ── LSL streams to record per block ─────────────────────────
    STREAM_NAMES = [
        "Polar H10 78117925",
        "pupil_capture_pupillometry_only",
        "ExpMarker",
    ]
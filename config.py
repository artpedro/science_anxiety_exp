from pathlib import Path

class Config:
    SCREEN = 1

    # ── Timing parameters (seconds) ─────────────────────────────
    PRE_QUESTION_WAIT      = 0.5
    NOISE_TO_QUESTION_WAIT = 0.5
    INTERACTIVE_DURATION   = 0.5
    POST_QUESTION_WAIT     = 0.5
    INPUT_DURATION         = 0.5

    # ── File-system layout ─────────────────────────────────────
    BASE_DATA_DIR         = Path("./patients")
    HIGH_BLOCK_AUDIO      = Path("./data/marker_audio/hard.wav")
    LOW_BLOCK_AUDIO       = Path("./data/marker_audio/easy.wav")
    END_BLOCK_AUDIO       = Path("./data/marker_audio/bell.wav")
    

    GLOBAL_QUESTIONS_DIR  = Path("./data/questions")  # parent for science_questions
    GLOBAL_METADATA_CSV   = Path("./data/metadata.csv")

    # ── Display settings ───────────────────────────────────────
    FULLSCREEN            = True
    WINDOW_SIZE           = (900, 600)
    WINDOW_COLOR          = "gray"           # gray background for cross
 
    # ── Visual-stim text settings ─────────────────────────────
    STIM_TEXT            = "+"              # cross shape
    STIM_COLOR           = "black"          # black cross on gray
    STIM_HEIGHT          = 0.2
    START_TEXT           = "-"
    START_TEXT_HEIGHT    = 0.1

    # ── LSL streams to record per block ─────────────────────────
    STREAM_NAMES = [
        "Polar H10 78117925",
        "pupil_capture_pupillometry_only",
        "ExpMarker",
    ]
     # ── New flags for stream checking ──────────────────────────
    WAIT_FOR_STREAMS      = False       # only start when all streams present
    STREAM_CHECK_TIMEOUT  = 2.0        # secs to wait when resolving each stream
    STREAM_CHECK_INTERVAL = 5.0        # secs to pause before retrying
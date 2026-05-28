
# Sermon Processing Pipeline

This document visualizes the end-to-end pipeline for processing public domain sermons into text, audio, and video content.

```mermaid
graph TD
    subgraph A[1. Sermon Acquisition]
        direction LR
        A1(Manual Trigger) -- or --> A2(Cron Job);
        A2 -- invokes --> A3{LLM Sermon Finder};
        A3 -- finds & formats --> A4[Sermon Texts (.md)];
    end

    subgraph B[2. Pre-processing & Cataloging]
        direction LR
        A4 -- read by --> B1(Processing Scripts e.g., generate_sermon_batch.py);
        B1 -- creates --> B2[Catalog (sermons.jsonl)];
    end

    subgraph C[3. Audio Generation (TTS Branches)]
        direction TD
        B2 -- provides text to --> C_ROUTER{Audio Generation};
        C_ROUTER --> C1[XTTS Model];
        C_ROUTER --> C2[Qwen3 TTS Model];
        C_ROUTER --> C3[Fish-Speech Model];
        C_ROUTER --> C4[Kaggle Pipeline (deprecated)];
        C1 --> C_OUT[Generated Audio (.wav)];
        C2 --> C_OUT;
        C3 --> C_OUT;
        C4 --> C_OUT;
    end

    subgraph D[4. Final Products]
        direction LR
        A4 --> D1[Text Anthologies (.md)];
        C_OUT -- concatenated into --> D2[Audiobook Anthologies];
        C_OUT -- combined with --> D3(Video Templates & Assets);
        D3 --> D4[Long & Short Form Videos];
    end

    A --> B --> C --> D;

    style A4 fill:#cde4ff,stroke:#5a96ff
    style B2 fill:#cde4ff,stroke:#5a96ff
    style C_OUT fill:#cde4ff,stroke:#5a96ff
    style C4 fill:#ffcdd2,stroke:#f44336
    
    style D1 fill:#d5e8d4,stroke:#82b366
    style D2 fill:#d5e8d4,stroke:#82b366
    style D4 fill:#d5e8d4,stroke:#82b366

```

## Key Stages

1.  **Sermon Acquisition:** The pipeline starts with either a manual or scheduled trigger that uses an LLM to find and format sermons from public domain authors into markdown files.
2.  **Pre-processing & Cataloging:** These markdown files are then processed by scripts to create a structured catalog (`sermons.jsonl`), making them easy to manage.
3.  **Audio Generation (TTS Branches):** The cataloged text is fed into one of several Text-to-Speech (TTS) models to generate audio files. This is the "branching" stage where different TTS technologies can be used and tested. The Kaggle pipeline is marked as a deprecated branch.
4.  **Final Products:** The raw assets (text and audio) are used to create the final outputs:
    *   **Text Anthologies:** Collections of sermon texts on specific topics.
    *   **Audiobook Anthologies:** The generated audio files are combined to create audiobooks.
    *   **Video Content:** The audio is mixed with video templates and assets to produce long and short-form videos.

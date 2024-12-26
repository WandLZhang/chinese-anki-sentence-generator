# Cantonese-Mandarin Sentence Generator

This project generates natural Cantonese and Mandarin example sentences for vocabulary learning, specifically designed for creating Anki cards. It uses Google's Vertex AI (Gemini) for RAG retrieval and Mandarin sentences, and Claude 3.5 Sonnet v2 for generating authentic Cantonese sentences based on Words.HK dictionary entries.

## Prerequisites

- Google Cloud Project with Vertex AI API enabled
- Access to Anthropic's Claude on Vertex AI
- Python 3.8+

## Setup

1. Install requirements:
```bash
pip3 install anthropic[vertex] vertexai google-cloud-aiplatform
```

2. Set environment variables:
```bash
export VERTEX_PROJECT_ID="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/credentials.json"
```

3. Create RAG Corpus:
- Download and parse the Words.HK dictionary entries from https://words.hk/faiman/request_data/
- Place the parsed entries in a folder named `dictionary_entries`
- Run the RAG corpus creation script:
```bash
python3 rag_corpus_confirm.py
```

4. Prepare Input Vocabulary:
- Create an `input.txt` file with your vocabulary list
- Each word should be followed by a tab and a newline
- Example format:
```
姑且    
古怪    
顾虑    
惯例    
固然    
```

## Usage

Run the sentence generator:
```bash
python3 generate-sentences.py
```

This will:
1. Convert Simplified Chinese to Traditional Chinese
2. Look up entries in the Words.HK dictionary via RAG
3. Generate a natural Mandarin sentence using Gemini
4. Generate an authentic Cantonese sentence using Claude
5. Output results to `output.txt` in a format ready for Anki import

## Output Format

The output file will contain tab-separated entries:
```
vocabulary_word    Mandarin sentence<br><br>Cantonese sentence
```

Example:
```
姑且    姑且答应他的要求吧。<br><br>暫時應承佢先啦。
```

## Notes

- The Cantonese generator prioritizes natural spoken Cantonese over literal translations
- Book/formal Chinese words (書面語) are automatically replaced with colloquial alternatives
- The system uses Words.HK entries to ensure authentic Cantonese usage

## Dictionary Data

The Words.HK dictionary data is provided under Creative Commons Attribution 4.0 International License. Please refer to https://words.hk for terms of use and attribution requirements.

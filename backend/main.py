import functions_framework
from flask import jsonify, request
from vertexai.preview import rag
from vertexai.preview.generative_models import GenerativeModel, SafetySetting
import vertexai
from anthropic import AnthropicVertex
from google.cloud import firestore
import os
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Vertex AI
PROJECT_ID = "wz-data-catalog-demo"
LOCATION = "us-central1"

# Initialize Firestore
db = firestore.Client()

# Initialize AnthropicVertex client
client = AnthropicVertex(
    region="us-east5",
    project_id=PROJECT_ID
)

def initialize_vertexai():
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        logger.info("Vertex AI initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}")
        raise

def get_rag_corpus():
    try:
        corpora = rag.list_corpora()
        corpus_list = list(corpora)
        
        if not corpus_list:
            logger.error("No RAG corpora found in the project")
            return None
        
        return corpus_list[0].name
    except Exception as e:
        logger.error(f"Error retrieving RAG corpus: {e}")
        return None

def simplified_to_traditional(simplified_text):
    model = GenerativeModel("gemini-1.5-flash-001")
    prompt = f"""
    Convert the following Simplified Chinese text to Traditional Chinese:
    {simplified_text}

    Output only the converted Traditional Chinese text, without any additional explanation or formatting.
    """
    try:
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error converting to Traditional Chinese: {e}")
        return simplified_text

def perform_rag_retrieval(corpus_name, vocabulary_word):
    try:
        response = rag.retrieval_query(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=corpus_name,
                )
            ],
            text=vocabulary_word,
            similarity_top_k=3,
            vector_distance_threshold=0.5,
        )
        return response
    except Exception as e:
        logger.error(f"Error performing RAG retrieval: {e}")
        return None

def find_best_entry(contexts, vocabulary_word: str):
    """Find the best matching entry from all retrieved contexts."""
    if not contexts:
        return "", False, False, []
        
    # First try to find an exact match
    for context in contexts:
        text = context.text.strip()
        match = re.match(r'^\d+,([^:]+):', text)
        if match and match.group(1) == vocabulary_word:
            is_formal = any(marker in text for marker in [
                "(label:書面語)",
                "(label:大陸)",
                "!!!formal"
            ])
            alternatives = []
            sim_matches = re.findall(r'\(sim:([^)]+)\)', text)
            alternatives.extend(sim_matches)
            return text, True, is_formal, alternatives
            
    # If no exact match found, return first context
    text = contexts[0].text.strip()
    is_formal = any(marker in text for marker in [
        "(label:書面語)",
        "(label:大陸)",
        "!!!formal"
    ])
    alternatives = []
    sim_matches = re.findall(r'\(sim:([^)]+)\)', text)
    alternatives.extend(sim_matches)
    return text, False, is_formal, alternatives

def generate_cantonese_sentence(vocabulary_word, mandarin_model):
    corpus_name = get_rag_corpus()
    retrieved_entry = perform_rag_retrieval(corpus_name, vocabulary_word)
    
    retrieved_text = ""
    is_exact_match = False
    is_formal = False
    alternatives = []
    
    if retrieved_entry and retrieved_entry.contexts.contexts:
        retrieved_text, is_exact_match, is_formal, alternatives = find_best_entry(
            retrieved_entry.contexts.contexts, 
            vocabulary_word
        )
    
    mandarin_meaning = ""
    if not is_exact_match or is_formal:
        try:
            meaning_prompt = f"What is the core meaning of the word '{vocabulary_word}' in Mandarin? Give a brief 1-sentence definition."
            meaning_response = mandarin_model.generate_content(
                meaning_prompt,
                generation_config={"temperature": 0.2},
                safety_settings=safety_settings,
            )
            mandarin_meaning = meaning_response.text.strip()
        except Exception as e:
            logger.error(f"Error getting Mandarin meaning: {e}")
    
    system_instruction = f"""You are a natural Cantonese language generator specializing in authentic Hong Kong Cantonese usage. Your task is to generate sentences that preserve the essential meaning and typical usage context of Mandarin words.

    Entry Type: {"Exact match" if is_exact_match else "No exact match"}
    Entry Formality: {"Formal/Written" if is_formal else "Colloquial"}
    {f'Mandarin Definition: {mandarin_meaning}' if mandarin_meaning else ''}

    Process for Sentence Generation:
    1. For formal/written entries (marked as 書面語, 大陸, or !!!formal):
    - DO NOT use the formal word in your sentence
    - Instead use these colloquial alternatives: {', '.join(alternatives) if alternatives else 'common spoken Cantonese expressions'}
    - Focus on natural spoken Cantonese that expresses the same meaning

    2. For colloquial entries:
    - Use the Words.HK entry as your guide
    - Ensure the usage matches typical Hong Kong speech

    Guidelines:
    - Focus on how Hong Kong Cantonese speakers would express the same idea in daily life
    - Keep the same level of formality and social context as the Mandarin usage
    - Ensure the sentence reflects a situation where this meaning would naturally occur

    Retrieved Dictionary Entry:
    {retrieved_text}

    IMPORTANT: Output ONLY the Cantonese sentence with NO additional text - no jyutping, no translation, no explanation."""

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-v2@20241022",
            max_tokens=100,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": f"Input: {vocabulary_word}\nGenerate ONLY a single Cantonese sentence."
                }
            ],
            system=system_instruction
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Error generating Cantonese sentence with Claude: {e}")
        return None

def generate_mandarin_sentence(model, vocabulary_word):
    system_instruction = """
    You are a helpful and knowledgeable Mandarin language tutor specializing in vocabulary from the HSK exam. Your task is to assist learners by providing example sentences for given vocabulary words (词语). For each input word in Simplified Chinese, you will output one sentence: A sentence in Simplified Chinese demonstrating the usage of the word within a clear and meaningful context. Avoid overly simplistic sentences that don't showcase the word's meaning effectively.

    Follow the format below for your responses:

    Input: [Simplified Chinese vocabulary word]
    Output: [Simplified Chinese sentence]

    Do not repeat the prompt input in your response.
    You must use the vocabulary word given, no replacements.
    """

    prompt = f"{system_instruction}\n\nInput: {vocabulary_word}"
    try:
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating Mandarin sentence: {e}")
        return None

# Generation configuration
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 2,
    "top_p": 0.95,
}

# Safety settings
safety_settings = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE
    ),
]

@functions_framework.http
def generate_sentences(request):
    # Set CORS headers for preflight requests
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Set CORS headers for main requests
    headers = {
        'Access-Control-Allow-Origin': '*'
    }

    # Handle main request
    try:
        request_json = request.get_json()
        if not request_json or 'word' not in request_json:
            return (jsonify({'error': 'No word provided'}), 400, headers)

        vocabulary_word = request_json['word']
        
        # Initialize Vertex AI
        initialize_vertexai()
        
        # Initialize Gemini model for Mandarin sentences
        mandarin_model = GenerativeModel("gemini-1.5-flash-001")
        
        # Generate sentences
        traditional_word = simplified_to_traditional(vocabulary_word)
        mandarin_sentence = generate_mandarin_sentence(mandarin_model, vocabulary_word)
        cantonese_sentence = generate_cantonese_sentence(traditional_word, mandarin_model)
        
        if not mandarin_sentence or not cantonese_sentence:
            return (jsonify({'error': 'Failed to generate sentences'}), 500, headers)
            
        # Create document in Firestore with timestamp
        doc_ref = db.collection('vocabulary').document()
        doc_ref.set({
            'simplified': vocabulary_word,
            'mandarin': mandarin_sentence,
            'cantonese': cantonese_sentence,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        return (jsonify({
            'simplified': vocabulary_word,
            'mandarin': mandarin_sentence,
            'cantonese': cantonese_sentence
        }), 200, headers)
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return (jsonify({'error': str(e)}), 500, headers)

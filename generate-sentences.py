from vertexai.preview import rag
from vertexai.preview.generative_models import GenerativeModel, Tool, SafetySetting
import vertexai
import logging
import os
from dotenv import load_dotenv
from anthropic import AnthropicVertex
import re

# Load environment variables
load_dotenv()

# Use environment variables instead of hardcoded values
PROJECT_ID = os.getenv('VERTEX_PROJECT_ID')
LOCATION = "us-central1"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        if len(corpus_list) > 1:
            logger.warning(f"Multiple RAG corpora found. Using the first one: {corpus_list[0].name}")
        
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
        return simplified_text  # Fallback to original text if conversion fails

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

def create_rag_retrieval_tool(corpus_name):
    try:
        return Tool.from_retrieval(
            retrieval=rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[
                        rag.RagResource(
                            rag_corpus=corpus_name,
                        )
                    ],
                    similarity_top_k=3,
                    vector_distance_threshold=0.5,
                ),
            )
        )
    except Exception as e:
        logger.error(f"Error creating RAG retrieval tool: {e}")
        return None

def check_entry_details(retrieved_text: str, vocabulary_word: str) -> tuple[bool, str]:
    """
    Check if the retrieved entry matches the vocabulary word and determine entry type.
    Returns (is_exact_match, entry_type) where entry_type can be:
    - "exact": Exact character match found
    - "similar": Entry appears to be semantically related
    - "unrelated": Entry appears to be unrelated
    """
    if not retrieved_text:
        return False, "unrelated"
        
    # Extract the entry word from the first line
    match = re.match(r'^\d+,([^:]+):', retrieved_text)
    if not match:
        return False, "unrelated"
        
    entry_word = match.group(1)
    if entry_word == vocabulary_word:
        return True, "exact"
    
    # If not exact match, check if the entry appears related
    # This is a heuristic - if the entry contains the vocabulary word in its definitions
    # or examples, it might be semantically related
    if vocabulary_word in retrieved_text:
        return False, "similar"
        
    return False, "unrelated"

def generate_cantonese_sentence(vocabulary_word, mandarin_model):
    # First get the dictionary entry using existing Gemini RAG
    corpus_name = get_rag_corpus()
    retrieved_entry = perform_rag_retrieval(corpus_name, vocabulary_word)
    
    # Format the retrieved entries for the prompt
    retrieved_text = ""
    if retrieved_entry and retrieved_entry.contexts.contexts:
        retrieved_text = retrieved_entry.contexts.contexts[0].text.strip()
    
    logger.info(f"Retrieved text: {retrieved_text}")
    
    # Check entry match type
    is_exact_match, entry_type = check_entry_details(retrieved_text, vocabulary_word)
    
    # Get Mandarin meaning if not exact match
    mandarin_meaning = ""
    if not is_exact_match:
        try:
            meaning_prompt = f"What is the core meaning of the word '{vocabulary_word}' in Mandarin? Give a brief 1-sentence definition."
            meaning_response = mandarin_model.generate_content(
                meaning_prompt,
                generation_config={"temperature": 0.2},  # Low temperature for consistent definition
                safety_settings=safety_settings,
            )
            mandarin_meaning = meaning_response.text.strip()
            logger.info(f"Mandarin meaning: {mandarin_meaning}")
        except Exception as e:
            logger.error(f"Error getting Mandarin meaning: {e}")
    
    # Initialize Vertex AI Claude client
    client = AnthropicVertex(
        region="us-east5",
        project_id=PROJECT_ID
    )
    
    system_instruction = f"""You are a natural Cantonese language generator specializing in authentic Hong Kong Cantonese usage. Your task is to generate sentences that preserve the essential meaning and typical usage context of Mandarin words.

    Entry Type: {"Exact match" if is_exact_match else "No exact match"}
    {f'Mandarin Definition: {mandarin_meaning}' if not is_exact_match else ''}

    Process for Sentence Generation:
    1. For exact matches: Use the Words.HK entry as your guide
    2. For non-exact matches:
    - Understand how and when the Mandarin word is typically used
    - Choose a Cantonese word/phrase that Hong Kong people would naturally use in the same situation
    - Create a scenario that shows this natural usage

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
    You are a helpful and knowledgeable Mandarin language tutor specializing in vocabulary from the HSK exam. Your task is to assist learners by providing example sentences for given vocabulary words (词语).  For each input word in Simplified Chinese, you will output one sentence: A sentence in Simplified Chinese demonstrating the usage of the word within a clear and meaningful context. Avoid overly simplistic sentences that don't showcase the word's meaning effectively.

    Follow the format below for your responses:

    Input: [Simplified Chinese vocabulary word]
    Output: [Simplified Chinese sentence]

    Do not repeat the prompt input in your response.
    You must use the vocabulary word given, no replacements.

    Here are a few examples to follow:

    Prompt: 出路
    Output: 投降是你唯一的出路。

    Prompt: 次序
    Output: 请你按次序上车。
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

def process_vocabulary_words(input_file, output_file):
    initialize_vertexai()

    # Get the RAG corpus
    corpus_name = get_rag_corpus()
    if not corpus_name:
        logger.error("Unable to proceed without a valid RAG corpus")
        return

    # Log the corpus details
    corpus = rag.get_corpus(name=corpus_name)
    logger.info(f"Using RAG corpus: {corpus}")
    
    # Initialize Gemini model for Mandarin sentences
    mandarin_model = GenerativeModel("gemini-1.5-flash-001")

    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            vocabulary_word = line.strip()
            if not vocabulary_word:
                continue

            traditional_word = simplified_to_traditional(vocabulary_word)
            logger.info(f"Processing: '{vocabulary_word}' ({traditional_word})")

            # Generate Mandarin sentence using Gemini
            mandarin_sentence = generate_mandarin_sentence(mandarin_model, vocabulary_word)

            # Generate Cantonese sentence using Claude on Vertex AI
            cantonese_sentence = generate_cantonese_sentence(traditional_word, mandarin_model)

            if mandarin_sentence and cantonese_sentence:
                output_line = f"{vocabulary_word}\t{mandarin_sentence}<br><br>{cantonese_sentence}\n"
                outfile.write(output_line)
                logger.info(f"Generated sentences for '{vocabulary_word}'")
            else:
                logger.warning(f"Failed to generate sentences for '{vocabulary_word}'")

    logger.info(f"Processing complete. Output written to {output_file}")

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

if __name__ == "__main__":
    input_file = "input.txt"
    output_file = "output.txt"
    process_vocabulary_words(input_file, output_file)

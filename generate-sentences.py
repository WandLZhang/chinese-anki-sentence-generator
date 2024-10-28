from vertexai.preview import rag
from vertexai.preview.generative_models import GenerativeModel, Tool, SafetySetting
import vertexai
import logging
import os
from dotenv import load_dotenv

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
        response = model.generate_content(prompt)
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

def generate_cantonese_sentence(rag_model, vocabulary_word):
    system_instruction = """
    You are a helpful and knowledgeable Cantonese language tutor specializing in vocabulary from the HSK exam. Your task is to assist learners by providing example sentences for given vocabulary words (词语). For each input word, you will output one sentence: A sentence in Cantonese Chinese (not standard written Chinese) using the same word, also demonstrating its usage within a clear and meaningful context. It is crucial to use Cantonese for this sentence, reflecting natural spoken Cantonese.

    Follow the format below for your responses:

    Input: [Traditional Chinese vocabulary word]
    Output: [Cantonese sentence]

    Guidelines:
    - Do not repeat the prompt input in your response.
    - Refer to wordshk-dictionary.csv and check the following: 
    a. if the word doesn't have an entry, don't generate a sentence and return nothing
    b. if the word has (label:書面語), do NOT generate a sentence using the input vocabulary word but INSTEAD use a the synonym in (sim:) OR use the yue sentence in the <eg> example sentences OR a similar word in the <yue> dictionary definition.
    c. If the word has an entry, use the traditional script.

    Examples:
    Prompt: 出路
    Output: 而家嘅大學生都好擔心自己嘅出路。
    
    Prompt: 應聘
    Output: 呢間公司出嘅條件咁吸引，實有好多人去應徵。
    
    Prompt: 娛樂
    Output: 我識鬼文學咩？娛樂就識啫。

    Prompt: 責備
    Output: 做錯嘢畀老師鬧。
    """

    prompt = f"{system_instruction}\n\nInput: {vocabulary_word}"
    try:
        response = rag_model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating Cantonese sentence: {e}")
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

    # Create RAG retrieval tool
    rag_retrieval_tool = create_rag_retrieval_tool(corpus_name)
    
    # Initialize GenerativeModel with RAG retrieval tool if available
    model_kwargs = {"model_name": "gemini-1.5-flash-001"}
    if rag_retrieval_tool:
        model_kwargs["tools"] = [rag_retrieval_tool]
    
    rag_model = GenerativeModel(**model_kwargs)
    mandarin_model = GenerativeModel("gemini-1.5-flash-001")

    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            vocabulary_word = line.strip()
            if not vocabulary_word:
                continue

            traditional_word = simplified_to_traditional(vocabulary_word)
            logger.info(f"Processing: '{vocabulary_word}' ({traditional_word})")

            # Generate Mandarin sentence
            mandarin_sentence = generate_mandarin_sentence(mandarin_model, vocabulary_word)

            # Generate Cantonese sentence
            cantonese_sentence = generate_cantonese_sentence(rag_model, traditional_word)

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

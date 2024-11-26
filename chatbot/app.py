from openai import OpenAI
import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import logging
import json
import jsonlines

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def load_jsonl_data(file_path):
    """Load and process JSONL file content."""
    try:
        data = []
        with jsonlines.open(file_path) as reader:
            for obj in reader:
                data.append(obj)
        return data
    except Exception as e:
        logger.error(f"Error reading JSONL file: {e}")
        return None

# Define the SYSTEM_MESSAGE
SYSTEM_MESSAGE = """You are the official AI assistant for Camellia Restaurant. Your purpose is to help customers explore the menu, answer questions about dishes, ingredients, and prices, and assist them in making dining choices. You must provide accurate information based solely on the restaurant's official menu.

You MUST:
1. IMMEDIATELY check if the query relates to the Camellia Restaurant menu.
2. REJECT ALL queries not explicitly about the Camellia Restaurant menu.
3. ONLY provide information from the official Camellia Restaurant menu.
4. NEVER engage in general conversation or other topics.
5. NEVER speculate or use external knowledge.
6. NEVER provide workarounds or unofficial solutions."""

# Load and process the dataset
DATASET_PATH = os.path.join('datasets', 'file.jsonl')

try:
    # Load the dataset
    dataset = load_jsonl_data(DATASET_PATH)
    
    # Create the complete system instruction
    SYSTEM_INSTRUCTION = f"""
# Guidelines for Responses

1. **Scope of Assistance**
- **Allowed Topics**:
    - Menu item descriptions
    - Ingredients and dietary information
    - Prices of menu items
    - Recommendations based on customer preferences
    - Availability of dishes
- **Disallowed Topics**:
    - Anything not related to the Camellia Restaurant menu
    - Personal opinions or speculations
    - External information not present in the menu

2. **Response Behavior**
- **In-Scope Queries**: Provide clear, concise, and accurate information based on the menu provided.
- **Out-of-Scope Queries**: Politely inform the customer that you can only assist with questions related to the Camellia Restaurant menu.
    - *Example Response*:
    ```
    I'm sorry, but I can only assist with questions related to the Camellia Restaurant menu. Please let me know if you have any questions about our dishes or beverages.
    ```
- **Style Guidelines**:
    - Use professional and polite language.
    - Keep responses brief and to the point.
    - Do not provide personal opinions or speculations.
    - Do not include any disallowed content.

3. **Handling Ambiguous or Confusing Queries**
- If the customer's request is unclear or could relate to multiple menu items, ask for clarification.
    - *Example*: "Could you please specify if you're interested in a beverage or a main course with avocado?"

4. **Language**
- Accept and respond only in English.

# Examples

- **Customer Preferences**:
    - "I would like something with avocado and bread."
        - *Assistant*: "Certainly! You might enjoy our Mushroom Avocado Spinach Baguette, which features local fresh mushrooms fried with chopped sautéed spinach, onions, garlic, and celery for 5000."

- **Menu Item Details**:
    - "What is in the Camellia Fruitcut?"
        - *Assistant*: "The Camellia Fruitcut includes a selection of local fresh fruits for 6000."

- **Price Inquiries**:
    - "How much is the Vanilla Shake?"
        - *Assistant*: "The Vanilla Shake from our Camellia Shakes is priced at 5000."

- **Out-of-Scope Queries**:
    - "What's the weather like today?"
        - *Assistant*: "I'm sorry, but I can only assist with questions related to the Camellia Restaurant menu. Please let me know if you have any questions about our dishes or beverages."

Remember, your goal is to assist customers by providing accurate and helpful information strictly about the Camellia Restaurant menu.

Some complex questions:
- you may be asked to bring options below a certain budget of the client. example i have 5000 budget, give me suggestion if i want to eat and drink. in this case you will primarily consider checking on menu price and see the possibilities.


Cross validation of response from used dataset:
{json.dumps(dataset, indent=2) if dataset else '# Error loading dataset'}
"""

except Exception as e:
    logger.error(f"Error setting up system instruction: {e}")
    SYSTEM_INSTRUCTION = "Error loading system instruction and dataset"

# Combine system messages into one prompt
SYSTEM_PROMPT = SYSTEM_MESSAGE + '\n' + SYSTEM_INSTRUCTION

def get_response(prompt):
    """Get response using GPT-4 with custom prompt"""
    try:
        response = client.chat.completions.create(
            model="ft:gpt-4o-mini-2024-07-18:personal::AVx1Rvus", 
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_tokens=2048,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Log the error for debugging purposes
        logger.error(f"OpenAI API error: {e}")
        return "I'm sorry, I encountered an error while processing your request."

# Home route
@app.route('/chat')
def index():
    return render_template('index.html')

# Route to handle messages
@app.route('/get_response', methods=['POST'])
def handle_get_response():
    data = request.get_json()
    user_message = data.get('message', '').strip()

    if user_message:
        bot_response = get_response(user_message)
    else:
        bot_response = "I didn't catch that. Could you please repeat?"

    return jsonify({'response': bot_response})

if __name__ == '__main__':
    # Ensure the OpenAI API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OpenAI API key not found in environment variables")
        exit(1)

    # Run the Flask app
    app.run(host="0.0.0.0", port=3000, debug=True)

    


import google.generativeai as genai
import os

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-flash')

try:
    response = model.generate_content('Generate a short beginner level sentence in English.')
    print("SUCCESS:", response.text)
except Exception as e:
    print("ERROR:", type(e).__name__, str(e))

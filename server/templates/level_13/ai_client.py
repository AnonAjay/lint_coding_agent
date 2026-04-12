import openai

# BROKEN: This is the old v0.28 syntax. 
# It will throw an AttributeError in the new v1.0+ environment.
def get_ai_response(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
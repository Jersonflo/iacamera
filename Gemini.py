import openai

class ChatBotApp:
    def __init__(self):
        # Configuración inicial de la API
        self.api_key = "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"
        openai.api_key = self.api_key

    def enviar_mensaje(self, question):
        """
        Envía la pregunta al modelo de IA y retorna la respuesta.
        """
        try:
            # Verifica que el modelo sea directamente especificado aquí
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", 
                messages=[{"role": "user", "content": question}]
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            return f"Ocurrió un error: {e}"




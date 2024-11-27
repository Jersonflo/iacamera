import google.generativeai as genai

class ChatBotApp:
    def __init__(self, direct_question=None):
        # Configuración inicial de la API y del modelo
        self.api_key = "AIzaSyDlSQAP7b7jYbCyFbAAjWaTVdByCq8rwzE"
        self.configure_api()
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
    def configure_api(self):
        """Configura la API con la clave proporcionada."""
        genai.configure(api_key=self.api_key)

    def enviar_mensaje(self, question):
        """
        Envía la pregunta al modelo de IA y retorna la respuesta.
        
        Args:
            question (str): La pregunta que el usuario hizo al chatbot.
        
        Returns:
            str: La respuesta generada por el modelo o un mensaje de error.
        """
        try:
            # Genera la respuesta usando el modelo de IA
            response = self.gemini_model.generate_content(question)
            return response.text
        except Exception as e:
            return f"Ocurrió un error: {e}"



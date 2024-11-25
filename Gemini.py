import ai21

class ChatBotApp:
    def __init__(self):
        # Configuración inicial de la API
        self.api_key = "G1wkjSO1q8vfeLINTejPLsjWw3MdUlMx"
        ai21.api_key = self.api_key


    def enviar_mensaje(self, question):
        """
        Envía la pregunta al modelo de IA de AI21 y retorna la respuesta.        
        """
        try:    
            # Verifica que el modelo sea directamente especificado aquí
            response = ai21.Completion.execute(
                model="j2-large",
                prompt=question,
                numResults=1,
                maxTokens=200,  # Ajusta el límite de tokens según tu necesidad
                temperature=0.7  # Controla la creatividad del modelo
            )
            # Devuelve el texto generado
            return response['completions'][0]['data']['text']
        except Exception as e:
            return f"Ocurrió un error: {e}"




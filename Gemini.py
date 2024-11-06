import streamlit as st
import google.generativeai as genai

class ChatBotApp:
    def __init__(self, direct_question=None):
        # Configuración inicial de la API y del modelo
        self.api_key = "AIzaSyA2DyBAOkP7xjp8TcHrHI1Xvv4QKShUkSw"
        self.configure_api()
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')

        # Configuración de la página
        self.configure_page()
        
        # Inicialización de la conversación en sesión
        if 'conversation' not in st.session_state:
            st.session_state.conversation = []
        
        # Cargar la interfaz y procesar el input del usuario
        if direct_question is None:
            self.show_header()
            self.show_chat_input()
            self.display_conversation()
            self.show_floating_buttons()
            self.show_footer()
        else:
            # Procesar la pregunta directa
            response = self.get_response(direct_question)
            print("Respuesta directa:", response)  # Solo para casos de pregunta directa

    def configure_api(self):
        genai.configure(api_key=self.api_key)

    def configure_page(self):
        st.set_page_config(page_title="Ecosystem Tech Bot", page_icon="🤖", layout="centered")
        self.apply_custom_css()

    def apply_custom_css(self):
        st.markdown(
            """
            <style>
            body { background-color: #291947; }
            div.stApp { background-color: #291947; color: #FFFFFF; }
            h1, h2, h3, p { color: #FFFFFF; }
            .logo { text-align: center; }
            .chat-message { display: flex; align-items: flex-start; margin-bottom: 15px; }
            .chat-user, .chat-bot {
                padding: 10px; border-radius: 15px; max-width: 70%; word-wrap: break-word;
            }
            .input-container {
                position: fixed; bottom: 10px; background-color: #291947;
                width: 80%; left: 50%;
            }
            div[data-testid="stChatInput"] {
                position: fixed; bottom: 10px; margin: 0 auto;
                background-color: #291947; color: white; border-radius: 10px; padding: 10px;
            }
            div[data-testid="stChatInput"] button {
                background-color: #dc3545; color: white; border: none; padding: 10px; border-radius: 5px;
            }
            .chat-user { background-color: #49DDC0; margin-left: 10px; }
            .chat-bot { background-color: #49DDC0; margin-right: 10px; margin-left: auto; }
            .chat-icon { width: 40px; height: 40px; margin-right: 10px; }
            .floating-buttons { position: fixed; bottom: 20px; left: 20px; display: flex; flex-direction: column; gap: 10px; }
            .floating-buttons img { width: 50px; height: 50px; cursor: pointer; }
            </style>
            """,
            unsafe_allow_html=True
        )

    def show_header(self):
        st.image("images\logo.png", use_column_width=True)

    def get_response(self, question):
        try:
            response = self.gemini_model.generate_content(question)
            return response.text
        except Exception as e:
            return f"Ocurrió un error: {e}"

    def show_chat_input(self):
        input_text = st.chat_input("Envía un mensaje a ChatBot Eco...")
        if input_text:
            st.session_state.conversation.append({"user": input_text, "bot": None})
            response = self.get_response(input_text)
            st.session_state.conversation[-1]["bot"] = response

    def display_conversation(self):
        with st.container():
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            for chat in st.session_state.conversation:
                if chat["user"]:
                    st.markdown(f"""
                    <div class="chat-message">
                        <img src="https://cdn-icons-png.flaticon.com/512/1077/1077012.png" class="chat-icon"/>
                        <div class="chat-user">{chat['user']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                if chat["bot"]:
                    st.markdown(f"""
                    <div class="chat-message">
                        <div class="chat-bot">{chat['bot']}</div>
                        <img src="https://cdn-icons-png.flaticon.com/512/4712/4712106.png" class="chat-icon"/>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    def show_floating_buttons(self):
        st.markdown("""
        <div class="floating-buttons">
            <img src="https://cdn-icons-png.flaticon.com/512/992/992703.png" alt="botón1"/>
            <img src="https://cdn-icons-png.flaticon.com/512/992/992684.png" alt="botón2"/>
        </div>
        """, unsafe_allow_html=True)

    def show_footer(self):
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #FFFFFF;'>Desarrollado con 💻 por Ecosystem Tech</p>", unsafe_allow_html=True)
        if st.session_state.conversation:
            st.markdown(
                """
                <script>
                var chatContainer = document.querySelector('.chat-container');
                chatContainer.scrollTop = chatContainer.scrollHeight;
                </script>
                """,
                unsafe_allow_html=True
            )

# Ejecutar solo si se llama directamente
if __name__ == "__main__":
    pregunta_directa = None  # Define la pregunta aquí si se necesita respuesta sin interfaz
    if pregunta_directa:
        chatbot = ChatBotApp(direct_question=pregunta_directa)
        print("Respuesta directa:", chatbot.get_response(pregunta_directa))
    else:
        ChatBotApp()

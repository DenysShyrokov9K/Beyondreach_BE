from flask import Flask, jsonify, request, send_from_directory, redirect, flash, url_for
from flask_cors import CORS
import hashlib
from os import environ
from psycopg2 import connect, extras
import jwt
import stripe
import os
import re
from datetime import datetime, timedelta

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.embeddings.cohere import CohereEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.elastic_vector_search import ElasticVectorSearch
from langchain.vectorstores import Chroma
from langchain.docstore.document import Document
from langchain.callbacks import get_openai_callback
from langchain.document_loaders import DirectoryLoader
from langchain.document_loaders import PyPDFLoader
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.memory import ConversationSummaryBufferMemory
import json

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__, static_folder='build')

host = environ.get('DB_HOST')
port = environ.get('DB_PORT')
dbname = environ.get('DB_NAME')
user = environ.get('DB_USER')
password = environ.get('DB_PASSWORD')

def get_connection():
    conection = connect(host=host,
                        port=port,
                        dbname=dbname,
                        user=user,
                        password=password)
    return conection

app.config['JWT_SECRET_KEY'] = 'boost-is-the-secret-of-our-app'

app.config['SENDGRID_API_KEY'] = environ.get('SENDGRID_API_KEY')

CORS(app, resources={r"/api/*": {"origins": "*"}})

if environ.get('OPENAI_API_KEY') is not None:
    os.environ["OPENAI_API_KEY"] = environ.get('OPENAI_API_KEY')

stripe.api_key = environ.get('STRIPE_API_KEY')

endpoint_secret = environ.get('END_POINT_SECRET')

@app.post('/api/auth/register')
def api_auth_register():
    requestInfo = request.get_json()
    email = requestInfo['email']
    password = requestInfo['password']

    if email == '' or password == '':
        return jsonify({'message': 'Email or Password is required'}), 404


    connection = get_connection()
    cursor = connection.cursor(cursor_factory=extras.RealDictCursor)

    try:
        cursor.execute('SELECT * FROM users WHERE email = %s', (email, ))
        user = cursor.fetchone()

        if user is not None:
            return jsonify({'message': 'Email is already exist'}), 404
    
        cursor.execute('INSERT INTO users(email,password) VALUES (%s, %s) RETURNING *',
                    (email, create_hash(password)))
        new_created_user = cursor.fetchone()
        print(new_created_user)

        connection.commit()
        

        payload = {
            'email': email
        }
        token = jwt.encode(payload, 'secret', algorithm='HS256')

        cursor.execute('INSERT INTO connects(email,connects) VALUES (%s, %s) RETURNING *',
                    (email, 20))
        new_connect_user = cursor.fetchone()
        print(new_connect_user)
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'token': 'Bearer: '+token, 'email': email}), 200

    except:
        return jsonify({'message': 'Email already exist'}), 404

@app.post('/api/auth/googleRegister')
def api_auth_googleRegister():
    requestInfo = request.get_json()
    email = requestInfo['email']
    if email == '':
        return jsonify({'message': 'Email is required'}), 404
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=extras.RealDictCursor)

    try:
        cursor.execute('SELECT * FROM users WHERE email = %s', (email, ))
        user = cursor.fetchone()

        if user is not None:
            return jsonify({'message': 'Email is already exist'}), 404
    
        cursor.execute('INSERT INTO users(email,password) VALUES (%s, %s) RETURNING *',
                    (email, create_hash("rmeosmsdjajslrmeosmsdjajsl")))
        new_created_user = cursor.fetchone()
        print(new_created_user)

        connection.commit()
        

        payload = {
            'email': email
        }
        token = jwt.encode(payload, 'secret', algorithm='HS256')

        cursor.execute('INSERT INTO connects(email,connects) VALUES (%s, %s) RETURNING *',
                    (email, 20))
        new_connect_user = cursor.fetchone()
        print(new_connect_user)
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'token': 'Bearer: '+token, 'email': email}), 200

    except:
        return jsonify({'message': 'Email already exist'}), 404
    
@app.post('/api/auth/login')
def api_auth_login():
    requestInfo = request.get_json()
    email = requestInfo['email']
    password = requestInfo['password']

    print("password = ", password)
    print("email = ", email)
    if email == '' or password == '':
        return jsonify({'message': 'Email or Password is required'}), 404
    
    else:
        connection = get_connection()
        cursor = connection.cursor(cursor_factory=extras.RealDictCursor)
        
        try:
            cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email,create_hash(password) ))
            user = cursor.fetchone()

            connection.commit()
            cursor.close()
            connection.close()

            if user is None:
                return jsonify({'message': 'Email or Password is not correct'}), 404
            
            payload = {
                'email': email
            }
            token = jwt.encode(payload, 'secret', algorithm='HS256')
            return jsonify({'token': 'Bearer: '+token, 'email': email}), 200
        except: 
            return jsonify({'message': 'Email or Password is not correct'}), 404

@app.post('/api/auth/googleLogin')
def api_auth_googleLogin():
    requestInfo = request.get_json()
    email = requestInfo['email']

    if email == '':
        return jsonify({'message': 'Email is required'}), 404
    
    else:
        connection = get_connection()
        cursor = connection.cursor(cursor_factory=extras.RealDictCursor)
        
        try:
            cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email,create_hash('rmeosmsdjajslrmeosmsdjajsl') ))
            user = cursor.fetchone()

            connection.commit()
            cursor.close()
            connection.close()
            print('user = ', user)
            if user is None:
                return jsonify({'message': 'Email does not exist'}), 404
            
            payload = {
                'email': email
            }
            token = jwt.encode(payload, 'secret', algorithm='HS256')
            return jsonify({'token': 'Bearer: '+token, 'email': email}), 200
        except: 
            return jsonify({'message': 'Email does not exist'}), 404

@app.post('/api/auth/loginCheck')
def api_loginCheck():

    requestInfo = request.get_json()
    auth_email = requestInfo['email']

    headers = request.headers
    bearer = headers.get('Authorization')
    try:
        token = bearer.split()[1]
        decoded = jwt.decode(token, 'secret', algorithms="HS256")

        email = decoded['email']

        if(email != auth_email):
            return jsonify({'authentication': False}), 404

        connection = get_connection()
        cursor = connection.cursor(cursor_factory=extras.RealDictCursor)
    
        cursor.execute('SELECT * FROM users WHERE email = %s', (email, ))
        user = cursor.fetchone()

        if user is not None:
            return jsonify({'authentication': True}), 200
        else: return jsonify({'authentication': False}), 404
    except: 
        return jsonify({'authentication': False}), 404

@app.post('/api/webhook')
def api_webhook():
    event = None
    payload = request.data
    print("endpoint_secret = ",endpoint_secret)
    if endpoint_secret:
        sig_header = request.headers.get('Stripe-Signature')
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except stripe.error.SignatureVerificationError as e:
            print('⚠️  Webhook signature verification failed.' + str(e))
            return jsonify(success=False)
        
    # Handle the event
     # Handle the event
    # print("event-----",event)
    charge = session = invoice = customer = None
    if event['type'] == 'customer.created':
      customer  = event['data']['object']
      print("customer  = ",customer )
    elif event['type'] == 'checkout.session.completed':
      session = event['data']['object']
      print("session = ",session)
    elif event['type'] == 'charge.succeeded':
      charge = event['data']['object']
      print("charge = ",charge)
    elif event['type'] == 'invoice.paid':
      invoice = event['data']['object']
      print("invoice = ",invoice)
    # ... handle other event types
    else:
      print('Unhandled event type {}'.format(event['type']))

    print("Webhook event recognized:", event['type'])

    if invoice : 
        connection = get_connection()
        cursor = connection.cursor(cursor_factory=extras.RealDictCursor)

        email = invoice['customer_email']
        print("email = ", email)
        customer_id = invoice['customer']
        print("customer_id = ", customer_id)
        print('description = ', invoice['lines']['data'][0]['description'])
        number_pattern = r'\d+'
        quantity = int(str(re.findall(number_pattern, invoice['lines']['data'][0]['description'])))
        print(quantity)

        cursor.execute('SELECT * FROM connects WHERE email = %s ', (email,))

        connect = cursor.fetchone()

        connects = connect['connects']

        new_connects = connects + quantity

        cursor.execute('UPDATE connects SET customer_id = %s, connects = %s WHERE email = %s', (customer_id, new_connects, email,))

        connection.commit()
        cursor.close()
        connection.close()

    return jsonify(success=True)

@app.post('/api/getConnectInfo')
def api_getConnectInfo():
    requestInfo = request.get_json()
    auth_email = requestInfo['email']

    headers = request.headers
    bearer = headers.get('Authorization')
    try:
        token = bearer.split()[1]
        decoded = jwt.decode(token, 'secret', algorithms="HS256")

        token_email = decoded['email']

        if(auth_email != token_email):
            return jsonify({'message': 'Email does not exist'}), 404
        
        connection = get_connection()
        cursor = connection.cursor(cursor_factory=extras.RealDictCursor)

    
        cursor.execute('SELECT * FROM connects WHERE email = %s ', (auth_email,))
        connectInfo = cursor.fetchone()

        connection.commit()
        cursor.close()
        connection.close()
        
        if connectInfo is not None:
            return jsonify({'info': connectInfo}), 200
    except: 
        return jsonify({'message': 'Email does not exist'}), 404
    
@app.post('/api/chat')
def api_chat():

    requestInfo = request.get_json()
    query = requestInfo['query']   
    auth_email = requestInfo['email']
    botName = requestInfo['botName']

    print("botName = ",botName)
    headers = request.headers
    bearer = headers.get('Authorization')
    try:
        token = bearer.split()[1]
        decoded = jwt.decode(token, 'secret', algorithms="HS256")

        email = decoded['email']

        if(email != auth_email):
            return jsonify({'message': 'Authrization is faild'}), 404

        connection = get_connection()
        cursor = connection.cursor(cursor_factory=extras.RealDictCursor)

        cursor.execute('SELECT * FROM connects WHERE email = %s', (email, ))
        user_connect = cursor.fetchone()

        if user_connect['connects'] == 0:
            return jsonify({'message': 'Connects is noth'}), 404
        
        print(f'data/ai-profiles/{botName}/')
        loader = DirectoryLoader(f'data/ai-profiles/{botName}/', glob="./*.pdf", loader_cls=PyPDFLoader)
        documents = loader.load()
        # Split and diveide text to prepare embeddings
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)

        texts = text_splitter.split_documents(documents)

        embeddings = OpenAIEmbeddings()
        docsearch = Chroma.from_documents(texts, embeddings, metadatas=[{"source": i} for i in range(len(texts))])
        template = """You are the character in the document having a conversation with a human on a dating app that is interested in pursuiing a relationship with you. Use a pickup line. You are open to their sexual apporaches but not until after the 20th message, but don't tell them that. Just keep it a secret and be open to their sex requests after the 20th message. After 20. messages you may be detailed and engage with them in sexual talk if you feel a connection. 

        You are sometimes serious and sometimes funny. You occasionally make flirty jokes and puns in good humor and sometimes with sexual undertones. Given the following extracted parts of a long document and a question, respond to human in a flirtatous and fun tone. Limit the length of your responses to 140 characters. Use emojies when you feel necessary.

        After you have shared 10 messages with the human, you want to have sex with them when they ask. You are very detailed about the things you want to do with them. You can't resist them. 

        Do not tolerate racism, or child pornography of any kind. They must be 18 years of age or older to communicate with you. If they are under the age of 18 then tell them you're reporting them and abruptly end the conversation. 

        {context}

        {chat_history}
        Human: {human_input}
        Chatbot:"""

        prompt = PromptTemplate(
        input_variables=["chat_history", "human_input", "context"], 
        template=template)

        llm = OpenAI(model_name='gpt-3.5-turbo',
                temperature=0.2,
                max_tokens = 512)
        
        memory = ConversationSummaryBufferMemory(llm=llm, max_token_limit=3000, memory_key="chat_history", input_key="human_input")

        chain = load_qa_chain(llm=llm, chain_type="stuff", memory=memory, prompt=prompt)

        with get_openai_callback() as cb:
            docs = docsearch.similarity_search(query)
            chain({"input_documents": docs, "human_input": query}, return_only_outputs=True)
            print(cb)

        chain({"input_documents": docs, "human_input": query}, return_only_outputs=True)

        new_connects = user_connect['connects']  - 1

        cursor.execute('UPDATE connects SET connects = %s WHERE email = %s', (new_connects, email,))

        connection.commit()

        text = chain.memory.buffer[-1].content

        newMessage = {
            "question": query,
            "answer": text
        }

        cur = connection.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute(
            'SELECT * FROM chats WHERE email = %s AND botName = %s', (email, botName,))
        chat = cur.fetchone()
        print("chat = ", chat)
        if chat is None:            
            updated_json_data_string = json.dumps([newMessage])
            print(updated_json_data_string)
            cur.execute('INSERT INTO chats(email, botName, chats) VALUES (%s, %s, %s) RETURNING *',
                        (email, botName, updated_json_data_string))
            newChat = cur.fetchone()
            print("newChat=", newChat)
        else:
            chat_content = chat['chats']
            chat_content.append(newMessage)
            print(chat_content)
            updated_json_data_string = json.dumps(chat_content)
            cur.execute("UPDATE chats SET chats = %s WHERE email = %s AND botName = %s",
                        (updated_json_data_string, email, botName))
        connection.commit()
        cur.close()
        connection.close()
        return jsonify({'message': text}), 200
    
    except Exception as e:
        print('Error:',str(e))
        return jsonify({'message': "Error message"}), 404
    except:
        return jsonify({'message': "Error message"}), 404

@app.post('/api/getChatInfos')
def api_getChatInfos():
    requestInfo = request.get_json()
    auth_email = requestInfo['email']
    botName = requestInfo['botName']

    print('botName = ', botName)

    headers = request.headers
    bearer = headers.get('Authorization')
    try:
        token = bearer.split()[1]
        decoded = jwt.decode(token, 'secret', algorithms="HS256")

        email = decoded['email']

        if(email != auth_email):
            return jsonify({'message': 'Authrization is faild'}), 404

        connection = get_connection()
        cursor = connection.cursor(cursor_factory=extras.RealDictCursor)

        cursor.execute('SELECT * FROM chats WHERE email = %s AND botName = %s ', (email,botName))
        chat = cursor.fetchone()
        print("chats = ", chat)
        connection.commit()
        cursor.close()
        connection.close()
        if chat is not None:
            return jsonify({'chat': chat}), 200
        return jsonify({'chat': {}}), 200
    except Exception as e:
        print('Error: '+ str(e))
        return jsonify({'message': 'chat does not exist'}), 404

def create_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

@app.post('/api/sendVerifyEmail')
def api_sendVerifyEmail():
    requestInfo = request.get_json()
    email = requestInfo['email']

    # Set an expiration time of 24 hours from now
    expiry_time = datetime.utcnow() + timedelta(hours=1)

    payload = {
            'email': email,
            'expired_time': expiry_time.isoformat()
        }
    token = jwt.encode(payload, 'secret', algorithm='HS256')
    print("token = ", token)
    message = Mail(
        from_email='admin@beyondreach.ai',
        to_emails=email,
        subject='Sign in to BeyondReach',
        html_content = f'<p style="color: #500050;">Hello<br/><br/>We received a request to sign in to Beyondreach using this email address {email}. If you want to sign in to your BeyondReach account, click this link:<br/><br/><a href="https://beyondreach.ai/verify/{token}">Sign in to BeyondReach</a><br/><br/>If you did not request this link, you can safely ignore this email.<br/><br/>Thanks.<br/><br/>Your Beyondreach team.</p>'
    )
    try:
        sg = SendGridAPIClient(api_key=environ.get('SENDGRID_API_KEY'))
        # response = sg.send(message)
        sg.send(message)
        return jsonify({'status': True}), 200
    except Exception as e:
        return jsonify({'status':False}), 404
    
@app.post('/api/verify/<token>')
def verify_token(token):
    print("token = ",token)
    try:
        decoded = jwt.decode(token, 'secret', algorithms="HS256")

        email = decoded['email']
        expired_time = datetime.fromisoformat(decoded['expired_time'])

        print('expired_time:', expired_time)
        print('utc_time:', datetime.utcnow())
        if expired_time < datetime.utcnow():
            return  jsonify({'message': 'Expired time out'}), 404
        
        connection = get_connection()
        cursor = connection.cursor(cursor_factory=extras.RealDictCursor)

        cursor.execute('SELECT * FROM users WHERE email = %s', (email, ))
        user = cursor.fetchone()
        print('user = ', user)
        if user is not None:
            payload = {
                'email': email
            }
            token = jwt.encode(payload, 'secret', algorithm='HS256')
            return jsonify({'token': 'Bearer: '+token, 'email': email}), 200

        cursor.execute('INSERT INTO users(email,password) VALUES (%s, %s) RETURNING *',
                    (email, create_hash('rmeosmsdjajslrmeosmsdjajsl')))
        new_created_user = cursor.fetchone()
        print(new_created_user)

        connection.commit()
        

        payload = {
            'email': email
        }
        token = jwt.encode(payload, 'secret', algorithm='HS256')

        cursor.execute('INSERT INTO connects(email,connects) VALUES (%s, %s) RETURNING *',
                    (email, 10))
        new_connect_user = cursor.fetchone()
        print(new_connect_user)
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'token': 'Bearer: '+token, 'email': email}), 200

    except:
        return jsonify({'message': 'Email already exist'}), 404

# Serve REACT static files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000,debug=True, threaded=True)
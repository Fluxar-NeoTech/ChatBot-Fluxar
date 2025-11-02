# 🤖 ChatBot-Fluxar  
> Chatbot inteligente da NeoTech para o projeto Fluxar — com RAG, agentes e RPA  

---

## 🪄 Visão Geral  

O **ChatBot-Fluxar** é uma aplicação desenvolvida em **Python** pela empresa fictícia **NeoTech**, como parte do projeto interdisciplinar **Fluxar**.  
Seu objetivo é oferecer um **assistente inteligente** integrado ao site e ao painel analítico do projeto, com foco em automação e análise inteligente de dados.  

A aplicação utiliza técnicas de **RAG (Retrieval-Augmented Generation)**, **Agentes Inteligentes** e **RPA (Robotic Process Automation)**, permitindo que o chatbot responda com base em uma base vetorial atualizada e também execute tarefas automatizadas de backend.

---

## ⚙️ Funcionalidades Principais  

- 🧠 **Integração RAG (Retrieval-Augmented Generation)** — permite ao chatbot buscar informações em bases vetoriais antes de responder, garantindo maior precisão contextual.  
- 🧩 **Agentes inteligentes** — responsáveis por lidar com interações mais complexas e multietapas no fluxo de conversa.  
- 🤖 **Automação de processos (RPA)** — scripts automatizados para executar tarefas repetitivas integradas ao chatbot.  
- 🪶 **Geração e indexação de embeddings** — criação de vetores a partir de textos base, via `execucao_embbeding.py`.  
- 💬 **ChatBot funcional** — script principal `main.py` executa o servidor e a lógica de conversação.  
- 🐳 **Containerização via Docker** — ambiente padronizado e pronto para deploy.  
- 📦 **Gerenciamento de dependências** — feito via `requirements.txt`.  
- 🪪 **Licença MIT** — uso livre para fins educacionais e comerciais.  

---

## 🧱 Estrutura do Projeto  

```
ChatBot-Fluxar/
│
├── app/                      # Módulo principal da aplicação (funções, serviços, rotas)
├── execucao_embbeding.py     # Script para geração de embeddings
├── execucao_RPA.py           # Script de automação (RPA)
├── main.py                   # Ponto de entrada da aplicação
├── Dockerfile                # Configuração Docker para containerização
├── requirements.txt          # Dependências do projeto
└── LICENSE                   # Licença MIT
```

---

## 🚀 Como Executar o Projeto  

### 🔧 Pré-requisitos  

- Python 3.10+  
- Docker (opcional, para rodar em container)  
- Variáveis de ambiente configuradas (ex: chaves de API, caminhos da base vetorial, etc.)

---

### 💻 Instalação Local  

```bash
# Clone o repositório
git clone https://github.com/Fluxar-NeoTech/ChatBot-Fluxar.git
cd ChatBot-Fluxar

# Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate    # (Linux/Mac)
# ou
.\.venv\Scripts\activate     # (Windows)

# Instale as dependências
pip install -r requirements.txt

# Execute o chatbot
python main.py
```

---

### 🐳 Executar com Docker  

```bash
# Build da imagem
docker build -t chatbot-fluxar .

# Execução do container
docker run -p 8000:8000 chatbot-fluxar
```

---

## 🤝 Contribuição  

Contribuições são muito bem-vindas 💜  
Abra uma *issue* ou envie um *pull request* explicando sua proposta antes de implementar uma nova funcionalidade.  

---

## 📜 Licença  

Este projeto está sob a licença **MIT** — veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

# 🌍 English Version  

## 🤖 ChatBot-Fluxar  
> NeoTech’s intelligent chatbot for the Fluxar project — powered by RAG, agents, and RPA  

---

## 🪄 Overview  

**ChatBot-Fluxar** is a Python-based application developed by **NeoTech** as part of the interdisciplinary **Fluxar Project**.  
It serves as an **intelligent assistant** that integrates with the website and analytical dashboard, combining **AI reasoning** and **process automation**.  

The system leverages **RAG (Retrieval-Augmented Generation)**, **intelligent agents**, and **RPA (Robotic Process Automation)** to provide accurate, context-aware responses and automated task execution.

---

## ⚙️ Main Features  

- 🧠 **RAG Integration** — retrieves contextual information from vector databases before answering.  
- 🧩 **Intelligent Agents** — handle complex, multi-step conversational flows.  
- 🤖 **RPA Integration** — automated scripts to perform backend repetitive tasks.  
- 🪶 **Embeddings Generator** — creates and updates vector representations (`execucao_embbeding.py`).  
- 💬 **Main Chat Service** — runs through `main.py`.  
- 🐳 **Docker Support** — easy deployment using containers.  
- 📦 **Requirements Management** — handled via `requirements.txt`.  
- 🪪 **MIT License** — open-source for educational and commercial use.  

---

## 🧱 Project Structure  

```
ChatBot-Fluxar/
│
├── app/                      
├── execucao_embbeding.py     
├── execucao_RPA.py           
├── main.py                   
├── Dockerfile                
├── requirements.txt          
└── LICENSE                   
```

---

## 🚀 Getting Started  

### 🔧 Prerequisites  

- Python 3.10+  
- Docker (optional)  
- Environment variables properly configured  

---

### 💻 Local Installation  

```bash
git clone https://github.com/Fluxar-NeoTech/ChatBot-Fluxar.git
cd ChatBot-Fluxar

python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# or
.\.venv\Scripts\activate    # Windows

pip install -r requirements.txt
python main.py
```

---

### 🐳 Run with Docker  

```bash
docker build -t chatbot-fluxar .
docker run -p 8000:8000 chatbot-fluxar
```

---

## 🤝 Contributing  

Contributions are welcome!  
Please open an *issue* or submit a *pull request* with a brief explanation of your idea before implementing a major change.  

---

## 📜 License  

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

✨ *Developed with 💜 by NeoTech — for the Fluxar Project* ✨

# Harpia - Sistema de Auxílio de Pouso com Lógica Fuzzy

## 1. Introdução

A Harpia é um sistema de controle de voo experimental, baseado em Lógica Fuzzy, projetado para auxiliar pilotos durante a fase mais crítica do voo: o pouso. O sistema atua como um copiloto inteligente, fornecendo comandos calculados para o leme (rudder) e profundor (elevator) a fim de garantir um pouso suave e alinhado, especialmente em condições de vento de través.

O projeto foi desenvolvido com uma arquitetura idealizada para diferentes modelos de aeronaves de pequeno porte, bastando para isso a criação de novos arquivos de configuração.

### Principais Características

- Motor de Inferência Fuzzy: Utiliza a biblioteca [scikit-fuzzy](https://pypi.org/project/scikit-fuzzy) para implementar a lógica de controle.
- Controle em Série: Simula a ação de um piloto real, primeiro corrigindo o alinhamento com a pista (leme) e depois executando o flare (profundor).
- Arquitetura Modular: O código é separado em módulos com responsabilidades claras (motor fuzzy, interface com simulador, carregamento de perfis, etc).
- Perfis de Aeronave Configuráveis: Os parâmetros de cada aeronave (limites de velocidade, altitude, etc.) são definidos em arquivos JSON, tornando o sistema facilmente expansível.
- Regras Externalizadas: A base de conhecimento do sistema (as regras SE-ENTÃO) é definida em arquivos CSV, permitindo que a lógica de controle seja ajustada sem alterar o código-fonte.

## 2. Estrutura do Projeto

A estrutura do projeto é organizada da seguinte forma:

```plaintext
Harpia/
├── venv/                  # Ambiente virtual do Python
├── src/
│   ├── main.py            # Ponto de entrada principal do programa
│   ├── fuzzy_engine.py    # Classe principal do motor de inferência fuzzy
│   ├── airplane_profiles.py # Módulo para carregar perfis de aeronaves
│   ├── simulator_interface.py # Interface para comunicação com simuladores
│   └── config/
│       ├── profiles/
│       │   └── cessna_172.json
│       └── rules/
│           ├── cessna_172_rudder.csv
│           └── cessna_172_elevator.csv
├── requirements.txt       # Lista de dependências do projeto
└── README.md              # Este arquivo
```

## 3. Tutorial de Instalação e Execução

Siga os passos abaixo para configurar e rodar o projeto em seu ambiente local.

### Pré-requisitos

- Python 3.10 ou superior
- pip e venv (geralmente inclusos na instalação do Python)

### Passos para Instalação

Clone o Repositório:

```Bash
git clone https://github.com/LucasVChaves/Harpia.git
cd Harpia
```

Crie e Ative um Ambiente Virtual:
É uma boa prática isolar as dependências do projeto.

```Bash
# Criar o ambiente
python -m venv venv

# Ativar no Linux ou macOS
source venv/bin/activate

# Ativar no Windows (PowerShell)
.\venv\Scripts\Activate.ps1
```

Instale as Dependências:

```Bash
pip install -r requirements.txt
```

Como Rodar o Programa
Com o ambiente virtual ativado e as dependências instaladas, execute o programa a partir do diretório raiz do projeto (`Harpia/`):

```Bash
python -m src.main
```

O programa irá iniciar e apresentar o menu de seleção de perfis de aeronave.

## 4. Como Usar a Ferramenta

Ao executar o programa, você verá um menu interativo:

1. Seleção de Perfil: Uma lista de todas as aeronaves disponíveis (definidas nos arquivos .json em src/config/profiles/) será exibida.
2. Digite o Número: Insira o número correspondente ao perfil que deseja carregar.
3. Simulação em Loop: O programa iniciará o loop de controle, utilizando o DummySimulator para gerar dados de voo aleatórios. A cada ciclo, ele imprimirá no terminal os dados lidos dos "sensores" e os comandos calculados pelo motor fuzzy.
4. Encerrar: Pressione Ctrl+C para parar a simulação e encerrar o programa.

## 5. Roadmap Futuro

**Etapa 1**: Validação e Refinamento do Core System  
[ ] Implementar testes unitários para os módulos (pytest).  
[ ] Gerar e analisar visualmente as superfícies de controle (matplotlib).  
[ ] Aprimorar o tratamento de erros e exceções no código.  

**Etapa 2**: Integração com o Simulador de Voo (FlightGear)  
[ ] Instalar e configurar o ambiente do FlightGear com o Cessna 172.  
[ ] Implementar a interface de comunicação UDP em simulator_interface.py.  
[ ] Criar o protocolo de comunicação (mapeamento de propriedades).  
[ ] Realizar teste em malha aberta (apenas leitura de dados do simulador).  
[ ] Realizar teste em malha fechada (envio de comandos para o simulador).  

**Etapa 3**: Aprimoramento da Inteligência (Neuro-Fuzzy)  
[ ] Gerar um dataset de alta qualidade com voos manuais no FlightGear.  
[ ] Executar a clusterização (K-Means com Método do Cotovelo) sobre o novo dataset.  
[ ] Analisar as regras descobertas e integrá-las aos arquivos .csv.  
[ ] Validar o desempenho do sistema refinado em novos testes no simulador.  

**Etapa 4**: Expansão e Publicação  
[ ] Adicionar um novo perfil de aeronave.  
[ ] Criar o arquivo .json de perfil.  
[ ] Criar os arquivos .csv de regras.  
[ ] Definir e executar uma bateria de testes sistemáticos para coleta de métricas.  
[ ] Estruturar e escrever o artigo científico com a metodologia e os resultados.  

**Etapa Opcional**: Interface Gráfica (GUI)  
[ ] (Opcional) Abstrair a lógica de apresentação do main.py.  
[ ] (Opcional) Projetar o layout da interface gráfica.  
[ ] (Opcional) Implementar a GUI com Kivy, utilizando threading para o loop de controle.  

## 6. Como Contribuir para o Projeto

Este projeto foi projetado para ser extensível. As duas formas mais comuns de contribuição são adicionar novas aeronaves e refinar as regras de controle.

### Adicionando uma Nova Aeronave

Para adicionar suporte a uma nova aeronave (ex: "Embraer Corisco"), siga estes passos:

1. Crie o Perfil JSON:
2. Crie um novo arquivo .json em `src/config/profiles/`, por exemplo, *embraer_corisco.json*.
3. Preencha os parâmetros da aeronave (nome, ranges das variáveis) seguindo o modelo do cessna_172.json.
4. Crie os Arquivos de Regras CSV:
5. Crie os dois arquivos de regras em `src/config/rules/`: *embraer_corisco_rudder.csv* e *embraer_corisco_elevator.csv*.
6. Popule estes arquivos com as regras de inferência que fazem sentido para a dinâmica de voo desta nova aeronave.

É só isso! Ao rodar o main.py novamente, a nova aeronave aparecerá automaticamente no menu de seleção.

### Refinando as Regras de Controle

Você pode editar diretamente os arquivos .csv em src/config/rules/ para testar novas lógicas de controle. O formato é:

`antecedents,operator,consequent,result`

- antecedents: Condições da regra. Múltiplas condições são separadas por ; (ponto e vírgula). Ex: airspeed:low;descent_rate:high.
- operator: Operador lógico para combinar os antecedentes (& para E, | para OU).
- consequent: Nome da variável de saída. Ex: elevator_output.
- result: Termo linguístico da saída. Ex: pull_strong.

Após editar e salvar o arquivo .csv, basta rodar o programa novamente para que as novas regras sejam carregadas.

## 7. Licença

Este projeto está licenciado sob a Licença Apache 2.0. Veja o arquivo LICENSE para mais detalhes.

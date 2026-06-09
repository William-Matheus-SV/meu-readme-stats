import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

# Definição explícita do mock vazio para evitar quebras
DADOS_MOCK = []

def buscar_dados_github(token, username):
    if not token:
        print("ERRO: Token não encontrado")
        return None
        
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}
    query = """
    query($username: String!) {
      user(login: $username) {
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          nodes {
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
      }
    }
    """
    try:
        response = requests.post(url, json={"query": query, "variables": {"username": username}}, headers=headers)
        if response.status_code == 200:
            data = response.json()

            if 'data' in data and data['data'] and data['data'].get('user'):
                return data
            else:
                print(f"ERRO: Estrutura inesperada: {data}")
                return None  # <-- CORRIGIDO: Indentação alinhada corretamente
        else:
            print(f"ERRO: Status {response.status_code}")
            return None
    except Exception as e:
        print(f"ERRO na requisição: {e}")
        return None

def calcular_porcentagens(dados_github):
    if not dados_github or 'data' not in dados_github or not dados_github['data'] or not dados_github['data']['user']:
        return DADOS_MOCK

    repos = dados_github['data']['user']['repositories']['nodes']
    idiomas = {}
    total_size = 0
    
    for repo in repos:
        if not repo.get('languages'):
            continue
        for edge in repo['languages']['edges']:
            size = edge['size']
            name = edge['node']['name']
            color = edge['node']['color'] or "#cccccc"
            
            total_size += size
            if name in idiomas:
                idiomas[name]['size'] += size
            else:
                idiomas[name] = {'size': size, 'color': color}
    
    if total_size == 0:
        return DADOS_MOCK

    resultado = []
    for name, info in idiomas.items():
        pct = round((info['size'] / total_size) * 100, 2)
        resultado.append({"name": name, "size": pct, "color": info['color']})
    
    resultado.sort(key=lambda x: x['size'], reverse=True)
    return resultado[:6]

def gerar_svg(linguagens):
    if not linguagens:
        return """<svg width="300" height="150" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#1a1b26"/><text x="20" y="50" fill="red" font-family="sans-serif">Erro: Nenhuma linguagem encontrada</text></svg>"""
    
    col1 = linguagens[:3]
    col2 = linguagens[3:]
    
    legendas_html = ""
    y = 90
    for lang in col1:
        legendas_html += f"""
        <circle cx="20" cy="{y-4}" r="4" fill="{lang['color']}" />
        <text x="36" y="{y}" class="lang-text">{lang['name']} {lang['size']}%</text>
        """
        y += 20
    
    y = 90
    for lang in col2:
        legendas_html += f"""
        <circle cx="160" cy="{y-4}" r="4" fill="{lang['color']}" />
        <text x="176" y="{y}" class="lang-text">{lang['name']} {lang['size']}%</text>
        """
        y += 20
    
    barra_html = ""
    x_atual = 20
    for lang in linguagens[:5]:
        largura = (lang['size'] / 100) * 260
        if largura > 0:
            barra_html += f'<rect x="{x_atual}" y="55" width="{largura}" height="8" fill="{lang["color"]}" />'
            x_atual += largura
    
    return f"""<svg width="300" height="180" viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <clipPath id="borda">
                <rect x="20" y="55" width="260" height="8" rx="4"/>
            </clipPath>
        </defs>
        <style>
            .title {{ font: bold 14px sans-serif; fill: #ff757f; }}
            .lang-text {{ font: 12px sans-serif; fill: #a9b1d6; }}
        </style>
        <rect width="100%" height="100%" fill="#1a1b26" rx="6" stroke="#24283b" stroke-width="1"/>
        <text x="20" y="35" class="title">Most Used Languages</text>
        
        <rect x="20" y="55" width="260" height="8" fill="#414868" rx="4"/>
        <g clip-path="url(#borda)">
            {barra_html}
        </g>
        
        {legendas_html}
    </svg>"""

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_components = parse_qs(urlparse(self.path).query)
        username = query_components.get("username", ["william-matheus-sv"])[0]
        
        token_github = os.getenv("TOKEN_GITHUB")
        
        dados = buscar_dados_github(token_github, username)
        lista_langs = calcular_porcentagens(dados)
        svg_final = gerar_svg(lista_langs)
        
        self.send_response(200)
        self.send_header('Content-type', 'image/svg+xml')
        
        # Anti-cache estrito para evitar que o GitHub e o navegador mostrem dados misturados/antigos
        self.send_header('Cache-Control', 'max-age=0, no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        
        self.end_headers()
        self.wfile.write(svg_final.encode('utf-8'))
        return
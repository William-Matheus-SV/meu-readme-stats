from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

def buscar_dados_github(token, username):
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"bearer {token}"}
    query = """
    query($username: String!) {
      user(login: $username) {
        repositories(ownerAffiliations: OWNER, first: 100, isFork: false) {
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
        return response.json()
    except:
        return None

def calcular_porcentagens(dados_github):
    # Valores estáticos de fallback caso a API do GitHub falhe ou o token mije para trás
    dados_mock = [
        {"name": "TypeScript", "size": 28.71, "color": "#3178c6"},
        {"name": "CSS", "size": 20.99, "color": "#563d7c"},
        {"name": "Python", "size": 15.04, "color": "#3572A5"},
        {"name": "JavaScript", "size": 12.29, "color": "#f1e05a"},
        {"name": "C#", "size": 11.23, "color": "#178600"},
        {"name": "HTML", "size": 11.14, "color": "#e34c26"}
    ]
    
    if not dados_github or 'data' not in dados_github or not dados_github['data']['user']:
        return dados_mock

    repos = dados_github['data']['user']['repositories']['nodes']
    idiomas = {}
    total_size = 0

    for repo in repos:
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
        return dados_mock

    resultado = []
    for name, info in idiomas.items():
        pct = round((info['size'] / total_size) * 100, 2)
        resultado.append({"name": name, "size": pct, "color": info['color']})
    
    # Ordena pelas mais usadas
    resultado.sort(key=lambda x: x['size'], reverse=True)
    return resultado[:6] # Pega as top 6 igual ao seu modelo

def gerar_svg(linguagens):
    # Monta a barra colorida proporcional
    barra_html = ""
    x_atual = 20
    largura_total_barra = 260
    
    for lang in linguagens:
        largura_pedaco = (lang['size'] / 100) * largura_total_barra
        if largura_pedaco > 0:
            barra_html += f'<rect x="{x_atual}" y="55" width="{largura_pedaco}" height="8" fill="{lang["color"]}" />'
            x_atual += largura_pedaco

    # Monta a lista de legenda em duas colunas (Esquerda e Direita)
    legendas_html = ""
    for i, lang in enumerate(linguagens):
        # Coluna 0 (esquerda) ou Coluna 1 (direita)
        coluna = i % 2
        linha = i // 2
        
        x = 20 if coluna == 0 else 160
        y = 85 + (linha * 20)
        
        legendas_html += f"""
        <circle cx="{x}" cy="{y-4}" r="4" fill="{lang['color']}" />
        <text x="{x+12}" y="{y}" class="lang-text">{lang['name']} {lang['size']}%</text>
        """

    # Retorna o arquivo SVG final estruturado com o tema Tokyo Night original
    return f"""<svg width="300" height="150" viewBox="0 0 300 150" xmlns="http://www.w3.org/2000/svg">
        <style>
            .title {{ font: bold 14px sans-serif; fill: #ff757f; }}
            .lang-text {{ font: 12px sans-serif; fill: #a9b1d6; font-weight: 500; }}
        </style>
        <rect width="100%" height="100%" fill="#1a1b26" rx="6" stroke="#24283b" stroke-width="1"/>
        <text x="20" y="35" class="title">Most Used Languages</text>
        
        <g clip-path="url(#borda-fina)">
            <rect x="20" y="55" width="260" height="8" fill="#414868" rx="4"/>
            {barra_html}
        </g>
        
        {legendas_html}
    </svg>"""

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_components = parse_qs(urlparse(self.path).query)
        # Se quiser testar com outros usuários depois pelo link (?username=teste)
        username = query_components.get("username", ["william-matheus-sv"])[0]
        
       # Em vez de string pura, ele vai ler a variável de ambiente segura do Vercel
        import os
        token_github = os.getenv("SEU_TOKEN_AQUI")
        
        dados = buscar_dados_github(token_github, username)
        lista_langs = calcular_porcentagens(dados)
        svg_final = gerar_svg(lista_langs)
        
        self.send_response(200)
        self.send_header('Content-type', 'image/svg+xml')
        self.send_header('Cache-Control', 'max-age=7200, stale-while-revalidate=3600')
        self.end_headers()
        self.wfile.write(svg_final.encode('utf-8'))
        return
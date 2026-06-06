from flask import Flask, jsonify, request, send_from_directory, send_file, abort, render_template
from flask_cors import CORS
import json
import os
import secrets
from datetime import datetime, timedelta
import csv
import io
import uuid
from functools import wraps
import hashlib
from threading import Lock

# AJUSTE DE PASTAS PARA O RENDER
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

DATA_FILE = 'nira_data.json'
BACKUP_FOLDER = 'backups'
db_lock = Lock()

# ===================== CONFIGURAÇÕES =====================
CATEGORIES = [
    "youtube", "instagram", "twitter", "tiktok", "facebook", "pinterest", "linkedin", "reddit", "snapchat", "threads", "twitch", "discord",
    "chatgpt", "gemini", "grok", "claude", "deepseek", "mistral", "llama", "perplexity", "qwen", "copilot", "midjourney", "stable_diffusion", "suno",
    "freefire", "roblox", "genshin", "valorant", "minecraft", "pubg", "fortnite", "cod", "lol", "brawlstars",
    "proxies", "vpn", "emails", "phones", "cards", "billing", "accounts", "scripts", "templates", "bots", "checkers", "tools",
    "finance", "crypto", "streaming", "music", "news", "shopping", "automation", "seo", "marketing",
    "logs", "settings", "stats", "backups", "users", "api_keys", "tasks", "notifications"
]

# ===================== INICIALIZAÇÃO E PERSISTÊNCIA SECORES =====================
def init_db():
    with db_lock:
        if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
            os.makedirs(BACKUP_FOLDER, exist_ok=True)
            
            initial = {cat: [] for cat in CATEGORIES if cat not in ["logs", "settings", "stats", "backups", "users", "api_keys", "tasks", "notifications"]}
            
            initial["settings"] = {
                "theme": "dark",
                "auto_refresh": True,
                "language": "pt-BR",
                "last_backup": None,
                "panel_name": "NIRA PANEL",
                "version": "2.5.0"
            }
            initial["logs"] = [{"timestamp": datetime.now().isoformat(), "action": "Nira Quantum Core Initialized", "user": "system", "level": "info"}]
            initial["stats"] = {"total_items": 0, "last_update": datetime.now().isoformat()}
            initial["backups"] = []
            initial["users"] = []
            initial["api_keys"] = []
            initial["tasks"] = []
            initial["notifications"] = []

            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(initial, f, indent=2, ensure_ascii=False)

def load_data():
    with db_lock:
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            initial = {cat: [] for cat in CATEGORIES}
            initial["settings"] = {"theme": "dark", "version": "2.5.0"}
            initial["api_keys"] = []
            initial["logs"] = []
            return initial

def save_data(data):
    with db_lock:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def log_action(data, action: str, user: str = "system", level: str = "info"):
    if "logs" not in data:
        data["logs"] = []
    data["logs"].append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "user": user,
        "level": level
    })
    if len(data["logs"]) > 2000:
        data["logs"] = data["logs"][-1000:]

# ===================== MIDDLEWARES DE SEGURANÇA =====================
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY') or request.args.get('key')
        if not api_key:
            return jsonify({"error": "Acesso Negado: Chave não fornecida no Header X-API-KEY"}), 401
        
        data = load_data()
        valid_keys = [k for k in data.get("api_keys", []) if k.get("key") == api_key and k.get("status") == "active"]
        if not valid_keys:
            return jsonify({"error": "Chave Inválida ou Revogada pela Nira Core"}), 403
        return f(*args, **kwargs)
    return decorated

# ===================== SYSTEM ROTAS AJUSTADA FOR TEMPLATES =====================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({
        "status": "online",
        "version": "2.5.0",
        "timestamp": datetime.now().isoformat(),
        "engine": "Quantum Engine Active"
    })

# ===================== SISTEMA DINÂMICO DE APIS E VALIDATION =====================
@app.route('/api/verificarkey', methods=['POST'])
def verificar_key_publica():
    req_data = request.json or {}
    target_key = req_data.get("key")
    if not target_key:
        return jsonify({"authorization": False, "message": "Nenhuma chave foi enviada para validação."}), 400
        
    data = load_data()
    all_keys = data.get("api_keys", [])
    
    match = next((k for k in all_keys if k.get("key") == target_key), None)
    if match:
        if match.get("status") == "active":
            return jsonify({
                "status": "success",
                "status_key": "active",
                "authorization": True,
                "message": f"Chave vinculada a '{match.get('name')}' autenticada com sucesso no NIRA PANEL v2.5."
            })
        else:
            return jsonify({"authorization": False, "message": "Chave encontrada, mas está INATIVA/SUSPENSA."})
            
    return jsonify({"authorization": False, "message": "Chave inexistente no banco de dados local."})

@app.route('/api/generate_token', methods=['POST'])
def generate_token():
    data = load_data()
    new_token = f"nira_live_{secrets.token_hex(16)}"
    req_body = request.json or {}
    
    token_entry = {
        "id": len(data.get("api_keys", [])) + 1,
        "name": req_body.get("name", f"TERMINAL_{secrets.token_hex(3).upper()}"),
        "key": new_token,
        "plan": req_body.get("plan", "premium"),
        "added_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        "status": "active",
        "created_by": req_body.get("user", "admin")
    }
    
    data.setdefault("api_keys", []).append(token_entry)
    log_action(data, f"Chave instanciada com sucesso: {token_entry['name']} [{token_entry['plan']}]")
    save_data(data)
    
    return jsonify({"status": "success", "token": token_entry})

# ===================== SISTEMA AVANÇADO DE BACKUP =====================
@app.route('/api/backup', methods=['POST'])
def create_backup():
    data = load_data()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_nira_{timestamp}.json"
    backup_path = os.path.join(BACKUP_FOLDER, backup_filename)
    
    os.makedirs(BACKUP_FOLDER, exist_ok=True)
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    data.setdefault("backups", []).append({
        "id": len(data.get("backups", [])) + 1,
        "date": datetime.now().isoformat(),
        "file": backup_filename,
        "size": os.path.getsize(backup_path)
    })
    
    data["settings"]["last_backup"] = datetime.now().isoformat()
    log_action(data, f"Backup estrutural gerado: {backup_filename}")
    save_data(data)
    
    return jsonify({"status": "success", "backup_file": backup_filename})

# ===================== INTELIGÊNCIA ARTIFICIAL SIMULADA =====================
@app.route('/api/generate/text', methods=['POST'])
def generate_text():
    req_data = request.json or {}
    prompt = req_data.get("prompt")
    model = req_data.get("model", "grok")

    if not prompt:
        return jsonify({"error": "Prompt é obrigatório"}), 400

    generated = f"[NIRA AI - GENERATION SUCCESSFUL]\n\nModelo Alocado: {model.upper()}\nPrompt Recebido: '{prompt}'\n\nProcessamento concluído com estabilidade quântica. Nira Core retornou respostas válidas na árvore local."

    result = {
        "id": str(uuid.uuid4()),
        "model": model,
        "prompt": prompt,
        "result": generated,
        "generated_at": datetime.now().isoformat()
    }

    data_db = load_data()
    data_db.setdefault("tasks", []).append(result)
    log_action(data_db, f"Processamento de Prompt AI executado via {model}")
    save_data(data_db)

    return jsonify({"status": "success", "generated": result})

@app.route('/api/generate/image', methods=['POST'])
def generate_image():
    req_data = request.json or {}
    prompt = req_data.get("prompt")
    model = req_data.get("model", "midjourney")

    if not prompt:
        return jsonify({"error": "Prompt de imagem vazio"}), 400

    result = {
        "id": str(uuid.uuid4()),
        "model": model,
        "prompt": prompt,
        "image_url": f"https://picsum.photos/seed/{hash(prompt)}/800/800",
        "generated_at": datetime.now().isoformat()
    }

    data_db = load_data()
    data_db.setdefault("tasks", []).append(result)
    log_action(data_db, f"Renderização sintética executada: {model}")
    save_data(data_db)

    return jsonify({"status": "success", "generated": result})

# ===================== ROTAS DINÂMICAS ULTRA OTIMIZADAS =====================
@app.route('/api/data', methods=['GET'])
def get_all_data():
    return jsonify(load_data())

@app.route('/api/<category>', methods=['GET', 'POST'])
def handle_category(category):
    data = load_data()
    if category not in CATEGORIES and category not in data:
        return jsonify({"error": f"Categoria '{category}' inexistente no mapa do Nira OS"}), 400

    if request.method == 'POST':
        item = request.json or {}
        item.setdefault('id', len(data.get(category, [])) + 1)
        item.setdefault('added_at', datetime.now().isoformat())
        item.setdefault('status', 'active')
        item.setdefault('uuid', str(uuid.uuid4()))

        data.setdefault(category, []).append(item)
        log_action(data, f"Dataset incrementado na tabela: {category}")
        save_data(data)
        return jsonify({"status": "success", "item": item})

    items = data.get(category, [])
    search = request.args.get('search')
    limit = int(request.args.get('limit', 100))
    page = int(request.args.get('page', 1))

    if search:
        items = [x for x in items if search.lower() in json.dumps(x).lower()]

    start = (page - 1) * limit
    return jsonify({
        "items": items[start:start+limit],
        "total": len(items),
        "page": page,
        "pages": (len(items) + limit - 1) // limit
    })

@app.route('/api/<category>/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
def item_operations(category, item_id):
    data = load_data()
    if category not in data:
        return jsonify({"error": "Categoria não indexada"}), 404

    items = data[category]

    for i, item in enumerate(items):
        if item.get('id') == item_id:
            if request.method == 'DELETE':
                del data[category][i]
                log_action(data, f"Remoção física executada na ID {item_id} de {category}")
                save_data(data)
                return jsonify({"status": "success"})

            elif request.method == 'PUT':
                updated = request.json or {}
                data[category][i] = {**item, **updated, "updated_at": datetime.now().isoformat()}
                log_action(data, f"Atualização de payload na ID {item_id} de {category}")
                save_data(data)
                return jsonify({"status": "success", "item": data[category][i]})

            else:
                return jsonify(item)

    return jsonify({"error": "Registro não localizado no buffer"}), 404

# ===================== SISTEMA DE EXPORT / IMPORT INTEGRAL =====================
@app.route('/api/export/<category>', methods=['GET'])
def export_csv(category):
    data = load_data()
    items = data.get(category, [])
    if not items:
        return jsonify({"error": "Não há linhas de registro para exportar nesta tabela"}), 400

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=items[0].keys())
    writer.writeheader()
    writer.writerows(items)
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'nira_matrix_{category}_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@app.route('/api/import/<category>', methods=['POST'])
def import_data(category):
    data = load_data()
    new_items = request.json

    if not isinstance(new_items, list):
        return jsonify({"error": "Payload inválido. Esperada uma Array de objetos JSON"}), 400

    current = data.setdefault(category, [])
    start_id = len(current) + 1

    for idx, item in enumerate(new_items):
        item['id'] = start_id + idx
        item['added_at'] = datetime.now().isoformat()
        item['uuid'] = str(uuid.uuid4())
        current.append(item)

    log_action(data, f"Importação em massa concluída: {len(new_items)} itens alocados em {category}")
    save_data(data)
    return jsonify({"status": "success", "imported": len(new_items)})

# ===================== MÉTRICAS DO MOTOR E METADADOS =====================
@app.route('/api/stats', methods=['GET'])
def get_stats():
    data = load_data()
    total_items = sum(len(v) for k, v in data.items() if isinstance(v, list) and k not in ["logs", "backups", "notifications"])

    return jsonify({
        "total_items": total_items,
        "categories": len([k for k in data if isinstance(data[k], list)]),
        "last_update": datetime.now().isoformat(),
        "storage_size_bytes": os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0,
        "backups_count": len(data.get("backups", []))
    })

@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    data = load_data()
    return jsonify({
        "recent_logs": data.get("logs", [])[-15:],
        "recent_tasks": data.get("tasks", [])[-5:],
        "top_categories": {cat: len(data.get(cat, [])) for cat in list(CATEGORIES)[:10]}
    })

# ===================== INICIALIZAÇÃO DO NIX CORE EXECUTION =====================
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8084, debug=True)

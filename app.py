
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, os
from datetime import datetime, date
from functools import wraps
import config

app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","dev-only-change-this-secret")
DB="barber_pro.db"

class CompatConnection:
    def __init__(self, conn, postgres=False):
        self.conn=conn; self.postgres=postgres
    def execute(self, sql, params=()):
        if self.postgres:
            sql=sql.replace("?", "%s")
        return self.conn.execute(sql, params)
    def executemany(self, sql, seq):
        if self.postgres:
            sql=sql.replace("?", "%s")
            with self.conn.cursor() as cur:
                return cur.executemany(sql, seq)
        return self.conn.executemany(sql, seq)
    def executescript(self, script):
        return self.conn.execute(script)
    def commit(self): return self.conn.commit()
    def close(self): return self.conn.close()

def db():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        import psycopg
        from psycopg.rows import dict_row
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        return CompatConnection(psycopg.connect(database_url, row_factory=dict_row), True)
    return CompatConnection(sqlite3.connect(DB), False)

def init():
    c=db()
    postgres = bool(os.environ.get("DATABASE_URL"))
    if postgres:
        c.execute("CREATE TABLE IF NOT EXISTS usuarios(id SERIAL PRIMARY KEY,nome TEXT,email TEXT UNIQUE,senha TEXT,papel TEXT DEFAULT 'Administrador',ativo INTEGER DEFAULT 1);")
        c.execute("CREATE TABLE IF NOT EXISTS clientes(id SERIAL PRIMARY KEY,nome TEXT NOT NULL,telefone TEXT,email TEXT,aniversario TEXT,observacoes TEXT);")
        c.execute("CREATE TABLE IF NOT EXISTS barbeiros(id SERIAL PRIMARY KEY,nome TEXT NOT NULL,telefone TEXT,comissao REAL DEFAULT 40,ativo INTEGER DEFAULT 1);")
        c.execute("CREATE TABLE IF NOT EXISTS servicos(id SERIAL PRIMARY KEY,nome TEXT NOT NULL,duracao INTEGER DEFAULT 30,preco REAL DEFAULT 0,ativo INTEGER DEFAULT 1);")
        c.execute("CREATE TABLE IF NOT EXISTS agendamentos(id SERIAL PRIMARY KEY,cliente_id INTEGER,barbeiro_id INTEGER,servico_id INTEGER,data TEXT,hora TEXT,status TEXT DEFAULT 'Agendado',origem TEXT DEFAULT 'painel',observacoes TEXT);")
        c.execute("CREATE TABLE IF NOT EXISTS vendas(id SERIAL PRIMARY KEY,cliente_id INTEGER,barbeiro_id INTEGER,servico_id INTEGER,valor REAL,pagamento TEXT,data TEXT,hora TEXT,agendamento_id INTEGER);")
        c.execute("CREATE TABLE IF NOT EXISTS despesas(id SERIAL PRIMARY KEY,descricao TEXT NOT NULL,valor REAL NOT NULL,tipo TEXT NOT NULL DEFAULT 'Variável',data TEXT NOT NULL,recorrente INTEGER DEFAULT 0,observacoes TEXT);")
        try: c.execute("ALTER TABLE usuarios ADD COLUMN ativo INTEGER DEFAULT 1")
        except Exception: pass
    else:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,email TEXT UNIQUE,senha TEXT,papel TEXT DEFAULT 'Administrador',ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS clientes(id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT NOT NULL,telefone TEXT,email TEXT,aniversario TEXT,observacoes TEXT);
        CREATE TABLE IF NOT EXISTS barbeiros(id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT NOT NULL,telefone TEXT,comissao REAL DEFAULT 40,ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS servicos(id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT NOT NULL,duracao INTEGER DEFAULT 30,preco REAL DEFAULT 0,ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS agendamentos(id INTEGER PRIMARY KEY AUTOINCREMENT,cliente_id INTEGER,barbeiro_id INTEGER,servico_id INTEGER,data TEXT,hora TEXT,status TEXT DEFAULT 'Agendado',origem TEXT DEFAULT 'painel',observacoes TEXT);
        CREATE TABLE IF NOT EXISTS vendas(id INTEGER PRIMARY KEY AUTOINCREMENT,cliente_id INTEGER,barbeiro_id INTEGER,servico_id INTEGER,valor REAL,pagamento TEXT,data TEXT,hora TEXT,agendamento_id INTEGER);
        CREATE TABLE IF NOT EXISTS despesas(id INTEGER PRIMARY KEY AUTOINCREMENT,descricao TEXT NOT NULL,valor REAL NOT NULL,tipo TEXT NOT NULL DEFAULT 'Variável',data TEXT NOT NULL,recorrente INTEGER DEFAULT 0,observacoes TEXT);
        """)
        try: c.execute("ALTER TABLE usuarios ADD COLUMN ativo INTEGER DEFAULT 1")
        except Exception: pass
    # Legacy admin values -> new role names
    c.execute("UPDATE usuarios SET papel='Administrador' WHERE papel IS NULL OR papel='' OR LOWER(papel)='admin'")
    if not c.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
        c.execute("INSERT INTO usuarios(nome,email,senha,papel,ativo) VALUES(?,?,?,?,?)",("Administrador","admin@vipbarbearia.com","123456","Administrador",1))
    if not c.execute("SELECT 1 FROM servicos LIMIT 1").fetchone():
        rows=[("Corte",40,40),("Barba",30,30),("Corte + Barba",60,60),("Sobrancelha",15,15)]
        c.executemany("INSERT INTO servicos(nome,duracao,preco) VALUES(?,?,?)",rows)
    if not c.execute("SELECT 1 FROM barbeiros LIMIT 1").fetchone():
        c.executemany("INSERT INTO barbeiros(nome,comissao) VALUES(?,?)",[("Carlos",40),("Rafael",40)])
    c.commit(); c.close()

@app.context_processor
def inject_config():
    return {"cfg": config, "ROLE_ADMIN": ROLE_ADMIN, "ROLE_FIXED": ROLE_FIXED, "ROLE_EVENTUAL": ROLE_EVENTUAL, "can_edit": can_edit(), "is_admin": is_admin(), "can_insert": can_insert()}

def login_required(f):
    @wraps(f)
    def w(*a,**k):
        if not session.get("uid"): return redirect(url_for("login"))
        return f(*a,**k)
    return w

ROLE_ADMIN = "Administrador"
ROLE_FIXED = "Colaborador Fixo"
ROLE_EVENTUAL = "Colaborador Eventual"

ROLE_LABELS = {ROLE_ADMIN: ROLE_ADMIN, ROLE_FIXED: ROLE_FIXED, ROLE_EVENTUAL: ROLE_EVENTUAL}


def current_role():
    role = session.get("papel", ROLE_ADMIN)
    if role == "admin":
        return ROLE_ADMIN
    return role


def can_insert():
    return bool(session.get("uid"))


def can_edit():
    return current_role() in (ROLE_ADMIN, ROLE_FIXED)


def is_admin():
    return current_role() == ROLE_ADMIN


def permission_required(kind):
    def deco(f):
        @wraps(f)
        def w(*a,**k):
            if not session.get("uid"):
                return redirect(url_for("login"))
            allowed = (kind == "insert") or (kind == "edit" and can_edit()) or (kind == "admin" and is_admin())
            if not allowed:
                flash("Seu perfil não tem permissão para esta ação.")
                return redirect(request.referrer or url_for("dashboard"))
            return f(*a,**k)
        return w
    return deco

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        c=db(); u=c.execute("SELECT * FROM usuarios WHERE email=? AND senha=? AND COALESCE(ativo,1)=1",(request.form["email"],request.form["senha"])).fetchone(); c.close()
        if u:
            role = ROLE_ADMIN if u["papel"] in (None, "", "admin") else u["papel"]
            session["uid"]=u["id"]; session["nome"]=u["nome"]; session["papel"]=role
            return redirect(url_for("dashboard"))
        flash("E-mail ou senha inválidos.")
    return render_template("login.html")

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    c=db(); hoje=date.today().isoformat()
    fat=c.execute("SELECT COALESCE(SUM(valor),0) v FROM vendas WHERE data=?",(hoje,)).fetchone()["v"]
    atend=c.execute("SELECT COUNT(*) n FROM vendas WHERE data=?",(hoje,)).fetchone()["n"]
    ag=c.execute("SELECT COUNT(*) n FROM agendamentos WHERE data=? AND status!='Cancelado'",(hoje,)).fetchone()["n"]
    desp=c.execute("SELECT COALESCE(SUM(valor),0) v FROM despesas WHERE data=? OR (tipo='Fixa' AND recorrente=1 AND data<=?)",(hoje,hoje)).fetchone()["v"]
    prox=c.execute("""SELECT a.*,cl.nome cliente,b.nome barbeiro,s.nome servico,s.preco FROM agendamentos a
    LEFT JOIN clientes cl ON cl.id=a.cliente_id LEFT JOIN barbeiros b ON b.id=a.barbeiro_id
    LEFT JOIN servicos s ON s.id=a.servico_id WHERE a.data=? ORDER BY a.hora LIMIT 10""",(hoje,)).fetchall()
    c.close(); return render_template("dashboard.html",fat=fat,atend=atend,ag=ag,desp=desp,lucro=fat-desp,ticket=fat/atend if atend else 0,prox=prox,hoje=hoje)

@app.route("/clientes",methods=["GET","POST"])
@login_required
def clientes():
    c=db()
    if request.method=="POST":
        c.execute("INSERT INTO clientes(nome,telefone,email,aniversario,observacoes) VALUES(?,?,?,?,?)",(request.form["nome"],request.form.get("telefone",""),request.form.get("email",""),request.form.get("aniversario",""),request.form.get("observacoes",""))); c.commit(); flash("Cliente cadastrado.")
    rows=c.execute("SELECT * FROM clientes ORDER BY nome").fetchall(); c.close()
    return render_template("clientes.html",rows=rows,edit=None)

@app.route("/clientes/editar/<int:id>",methods=["GET","POST"])
@permission_required("edit")
def editar_cliente(id):
    c=db()
    if request.method=="POST":
        c.execute("UPDATE clientes SET nome=?,telefone=?,email=?,aniversario=?,observacoes=? WHERE id=?",(request.form["nome"],request.form.get("telefone",""),request.form.get("email",""),request.form.get("aniversario",""),request.form.get("observacoes",""),id)); c.commit(); c.close(); flash("Cliente atualizado."); return redirect(url_for("clientes"))
    edit=c.execute("SELECT * FROM clientes WHERE id=?",(id,)).fetchone(); rows=c.execute("SELECT * FROM clientes ORDER BY nome").fetchall(); c.close()
    return render_template("clientes.html",rows=rows,edit=edit)

@app.route("/clientes/excluir/<int:id>",methods=["POST"])
@permission_required("edit")
def excluir_cliente(id):
    c=db(); c.execute("DELETE FROM clientes WHERE id=?",(id,)); c.commit(); c.close(); flash("Cliente excluído."); return redirect(url_for("clientes"))

@app.route("/barbeiros",methods=["GET","POST"])
@login_required
def barbeiros():
    c=db()
    if request.method=="POST":
        c.execute("INSERT INTO barbeiros(nome,telefone,comissao) VALUES(?,?,?)",(request.form["nome"],request.form.get("telefone",""),request.form.get("comissao",40))); c.commit(); flash("Barbeiro cadastrado.")
    rows=c.execute("SELECT * FROM barbeiros ORDER BY nome").fetchall(); c.close(); return render_template("barbeiros.html",rows=rows,edit=None)

@app.route("/barbeiros/editar/<int:id>",methods=["GET","POST"])
@permission_required("edit")
def editar_barbeiro(id):
    c=db()
    if request.method=="POST":
        c.execute("UPDATE barbeiros SET nome=?,telefone=?,comissao=?,ativo=? WHERE id=?",(request.form["nome"],request.form.get("telefone",""),request.form.get("comissao",40),1 if request.form.get("ativo") else 0,id)); c.commit(); c.close(); flash("Barbeiro atualizado."); return redirect(url_for("barbeiros"))
    edit=c.execute("SELECT * FROM barbeiros WHERE id=?",(id,)).fetchone(); rows=c.execute("SELECT * FROM barbeiros ORDER BY nome").fetchall(); c.close(); return render_template("barbeiros.html",rows=rows,edit=edit)

@app.route("/barbeiros/excluir/<int:id>",methods=["POST"])
@permission_required("edit")
def excluir_barbeiro(id):
    c=db(); c.execute("DELETE FROM barbeiros WHERE id=?",(id,)); c.commit(); c.close(); flash("Barbeiro excluído."); return redirect(url_for("barbeiros"))

@app.route("/servicos",methods=["GET","POST"])
@login_required
def servicos():
    c=db()
    if request.method=="POST":
        c.execute("INSERT INTO servicos(nome,duracao,preco) VALUES(?,?,?)",(request.form["nome"],request.form.get("duracao",30),request.form.get("preco",0))); c.commit(); flash("Serviço cadastrado.")
    rows=c.execute("SELECT * FROM servicos ORDER BY nome").fetchall(); c.close(); return render_template("servicos.html",rows=rows,edit=None)

@app.route("/servicos/editar/<int:id>",methods=["GET","POST"])
@permission_required("edit")
def editar_servico(id):
    c=db()
    if request.method=="POST":
        c.execute("UPDATE servicos SET nome=?,duracao=?,preco=?,ativo=? WHERE id=?",(request.form["nome"],request.form.get("duracao",30),request.form.get("preco",0),1 if request.form.get("ativo") else 0,id)); c.commit(); c.close(); flash("Serviço atualizado."); return redirect(url_for("servicos"))
    edit=c.execute("SELECT * FROM servicos WHERE id=?",(id,)).fetchone(); rows=c.execute("SELECT * FROM servicos ORDER BY nome").fetchall(); c.close(); return render_template("servicos.html",rows=rows,edit=edit)

@app.route("/servicos/excluir/<int:id>",methods=["POST"])
@permission_required("edit")
def excluir_servico(id):
    c=db(); c.execute("DELETE FROM servicos WHERE id=?",(id,)); c.commit(); c.close(); flash("Serviço excluído."); return redirect(url_for("servicos"))

@app.route("/agenda",methods=["GET","POST"])
@login_required
def agenda():
    c=db(); d=request.args.get("data",date.today().isoformat())
    if request.method=="POST":
        cli,bar,ser,dt,hr=[request.form[x] for x in ("cliente","barbeiro","servico","data","hora")]
        if c.execute("SELECT 1 FROM agendamentos WHERE barbeiro_id=? AND data=? AND hora=? AND status!='Cancelado'",(bar,dt,hr)).fetchone():
            flash("Horário ocupado para este barbeiro.")
        else:
            c.execute("INSERT INTO agendamentos(cliente_id,barbeiro_id,servico_id,data,hora,origem) VALUES(?,?,?,?,?,?)",(cli,bar,ser,dt,hr,"painel")); c.commit(); flash("Agendamento criado.")
        return redirect(url_for("agenda",data=dt))
    rows=c.execute("""SELECT a.*,cl.nome cliente,b.nome barbeiro,s.nome servico,s.preco FROM agendamentos a
    LEFT JOIN clientes cl ON cl.id=a.cliente_id LEFT JOIN barbeiros b ON b.id=a.barbeiro_id LEFT JOIN servicos s ON s.id=a.servico_id WHERE a.data=? ORDER BY a.hora""",(d,)).fetchall()
    clients=c.execute("SELECT * FROM clientes ORDER BY nome").fetchall(); bars=c.execute("SELECT * FROM barbeiros WHERE ativo=1 ORDER BY nome").fetchall(); services=c.execute("SELECT * FROM servicos WHERE ativo=1 ORDER BY nome").fetchall(); c.close()
    return render_template("agenda.html",rows=rows,clientes=clients,barbeiros=bars,servicos=services,data=d)

@app.route("/agenda/editar/<int:id>",methods=["GET","POST"])
@permission_required("edit")
def editar_agendamento(id):
    c=db()
    if request.method=="POST":
        cli,bar,ser,dt,hr=[request.form[x] for x in ("cliente","barbeiro","servico","data","hora")]
        busy=c.execute("SELECT 1 FROM agendamentos WHERE barbeiro_id=? AND data=? AND hora=? AND status!='Cancelado' AND id!=?",(bar,dt,hr,id)).fetchone()
        if busy: flash("Horário ocupado para este barbeiro.")
        else:
            c.execute("UPDATE agendamentos SET cliente_id=?,barbeiro_id=?,servico_id=?,data=?,hora=?,observacoes=? WHERE id=?",(cli,bar,ser,dt,hr,request.form.get("observacoes",""),id)); c.commit(); c.close(); flash("Agendamento atualizado."); return redirect(url_for("agenda",data=dt))
    edit=c.execute("SELECT * FROM agendamentos WHERE id=?",(id,)).fetchone(); clients=c.execute("SELECT * FROM clientes ORDER BY nome").fetchall(); bars=c.execute("SELECT * FROM barbeiros WHERE ativo=1 ORDER BY nome").fetchall(); services=c.execute("SELECT * FROM servicos WHERE ativo=1 ORDER BY nome").fetchall(); c.close()
    return render_template("agenda_edit.html",edit=edit,clientes=clients,barbeiros=bars,servicos=services)

@app.route("/agenda/excluir/<int:id>",methods=["POST"])
@permission_required("edit")
def excluir_agendamento(id):
    c=db(); c.execute("DELETE FROM agendamentos WHERE id=?",(id,)); c.execute("DELETE FROM vendas WHERE agendamento_id=?",(id,)); c.commit(); c.close(); flash("Agendamento excluído."); return redirect(url_for("agenda"))

@app.route("/agenda/status/<int:id>/<status>")
@permission_required("edit")
def status(id,status):
    c=db(); c.execute("UPDATE agendamentos SET status=? WHERE id=?",(status,id))
    if status=="Concluído":
        a=c.execute("""SELECT a.*,s.preco FROM agendamentos a JOIN servicos s ON s.id=a.servico_id WHERE a.id=?""",(id,)).fetchone()
        if a and not c.execute("SELECT 1 FROM vendas WHERE agendamento_id=?",(id,)).fetchone():
            c.execute("INSERT INTO vendas(cliente_id,barbeiro_id,servico_id,valor,pagamento,data,hora,agendamento_id) VALUES(?,?,?,?,?,?,?,?)",
            (a["cliente_id"],a["barbeiro_id"],a["servico_id"],a["preco"],"A definir",a["data"],a["hora"],id))
    c.commit(); c.close(); return redirect(url_for("agenda"))

@app.route("/caixa",methods=["GET","POST"])
@login_required
def caixa():
    c=db(); d=request.args.get("data",date.today().isoformat())
    if request.method=="POST":
        c.execute("INSERT INTO vendas(cliente_id,barbeiro_id,servico_id,valor,pagamento,data,hora) VALUES(?,?,?,?,?,?,?)",
        (request.form.get("cliente_id") or None,request.form["barbeiro_id"],request.form.get("servico_id") or None,request.form["valor"],request.form["pagamento"],request.form["data"],datetime.now().strftime("%H:%M")))
        c.commit(); flash("Venda lançada.")
        return redirect(url_for("caixa",data=request.form["data"]))
    rows=c.execute("""SELECT v.*,cl.nome cliente,b.nome barbeiro,s.nome servico FROM vendas v LEFT JOIN clientes cl ON cl.id=v.cliente_id
    JOIN barbeiros b ON b.id=v.barbeiro_id LEFT JOIN servicos s ON s.id=v.servico_id WHERE v.data=? ORDER BY v.hora DESC""",(d,)).fetchall()
    total=c.execute("SELECT COALESCE(SUM(valor),0) v FROM vendas WHERE data=?",(d,)).fetchone()["v"]
    clientes=c.execute("SELECT * FROM clientes ORDER BY nome").fetchall(); bars=c.execute("SELECT * FROM barbeiros WHERE ativo=1 ORDER BY nome").fetchall(); services=c.execute("SELECT * FROM servicos WHERE ativo=1 ORDER BY nome").fetchall()
    c.close(); return render_template("caixa.html",rows=rows,total=total,clientes=clientes,barbeiros=bars,servicos=services,data=d)

@app.route("/caixa/editar/<int:id>",methods=["GET","POST"])
@permission_required("edit")
def editar_venda(id):
    c=db()
    if request.method=="POST":
        c.execute("UPDATE vendas SET cliente_id=?,barbeiro_id=?,servico_id=?,valor=?,pagamento=?,data=? WHERE id=?",(request.form.get("cliente_id") or None,request.form["barbeiro_id"],request.form.get("servico_id") or None,request.form["valor"],request.form["pagamento"],request.form["data"],id)); c.commit(); c.close(); flash("Venda atualizada."); return redirect(url_for("caixa",data=request.form["data"]))
    edit=c.execute("SELECT * FROM vendas WHERE id=?",(id,)).fetchone(); clientes=c.execute("SELECT * FROM clientes ORDER BY nome").fetchall(); bars=c.execute("SELECT * FROM barbeiros WHERE ativo=1 ORDER BY nome").fetchall(); services=c.execute("SELECT * FROM servicos WHERE ativo=1 ORDER BY nome").fetchall(); c.close(); return render_template("venda_edit.html",edit=edit,clientes=clientes,barbeiros=bars,servicos=services)

@app.route("/caixa/excluir/<int:id>",methods=["POST"])
@permission_required("edit")
def excluir_venda(id):
    c=db(); c.execute("DELETE FROM vendas WHERE id=?",(id,)); c.commit(); c.close(); flash("Venda excluída."); return redirect(url_for("caixa"))

@app.route("/relatorios")
@login_required
def relatorios():
    d=request.args.get("data",date.today().isoformat()); c=db()
    total=c.execute("SELECT COALESCE(SUM(valor),0) v FROM vendas WHERE data=?",(d,)).fetchone()["v"]
    despesas_total=c.execute("SELECT COALESCE(SUM(valor),0) v FROM despesas WHERE data=? OR (tipo='Fixa' AND recorrente=1 AND data<=?)",(d,d)).fetchone()["v"]
    formas=c.execute("SELECT pagamento, SUM(valor) total FROM vendas WHERE data=? GROUP BY pagamento",(d,)).fetchall()
    com=c.execute("""SELECT b.nome,SUM(v.valor) faturamento, b.comissao,
    SUM(v.valor)*b.comissao/100 comissao_valor FROM vendas v JOIN barbeiros b ON b.id=v.barbeiro_id WHERE v.data=? GROUP BY b.id""",(d,)).fetchall()
    serv=c.execute("""SELECT s.nome,COUNT(v.id) qtd,SUM(v.valor) total FROM vendas v JOIN servicos s ON s.id=v.servico_id WHERE v.data=? GROUP BY s.id ORDER BY total DESC""",(d,)).fetchall()
    c.close(); return render_template("relatorios.html",data=d,total=total,despesas_total=despesas_total,liquido=total-despesas_total,formas=formas,com=com,serv=serv)

@app.route("/configuracoes",methods=["GET","POST"])
@permission_required("admin")
def configuracoes():
    c=db(); u=c.execute("SELECT * FROM usuarios WHERE id=?",(session["uid"],)).fetchone()
    if request.method=="POST":
        nome=request.form["nome"].strip(); email=request.form["email"].strip(); senha=request.form.get("senha","").strip()
        if senha: c.execute("UPDATE usuarios SET nome=?,email=?,senha=? WHERE id=?",(nome,email,senha,session["uid"]))
        else: c.execute("UPDATE usuarios SET nome=?,email=? WHERE id=?",(nome,email,session["uid"]))
        c.commit(); session["nome"]=nome; session["email"]=email; session["papel"]=u["papel"] if u else session.get("papel"); flash("Dados do administrador atualizados."); u=c.execute("SELECT * FROM usuarios WHERE id=?",(session["uid"],)).fetchone()
    users=c.execute("SELECT id,nome,email,papel,COALESCE(ativo,1) ativo FROM usuarios ORDER BY nome").fetchall()
    c.close(); return render_template("configuracoes.html",usuario=u,users=users,roles=[ROLE_ADMIN,ROLE_FIXED,ROLE_EVENTUAL])


@app.route("/usuarios", methods=["GET", "POST"])
@permission_required("admin")
def usuarios():
    c=db()
    if request.method == "POST":
        nome=request.form["nome"].strip(); email=request.form["email"].strip(); senha=request.form["senha"].strip(); papel=request.form["papel"]
        if papel not in (ROLE_ADMIN, ROLE_FIXED, ROLE_EVENTUAL): papel=ROLE_EVENTUAL
        try:
            c.execute("INSERT INTO usuarios(nome,email,senha,papel,ativo) VALUES(?,?,?,?,?)",(nome,email,senha,papel,1)); c.commit(); flash("Usuário criado com sucesso.")
        except Exception:
            flash("Não foi possível criar o usuário. Verifique se o e-mail já está cadastrado.")
    rows=c.execute("SELECT id,nome,email,papel,COALESCE(ativo,1) ativo FROM usuarios ORDER BY nome").fetchall(); c.close()
    return render_template("usuarios.html", rows=rows, roles=[ROLE_ADMIN,ROLE_FIXED,ROLE_EVENTUAL])

@app.route("/usuarios/status/<int:id>", methods=["POST"])
@permission_required("admin")
def usuario_status(id):
    if id == session.get("uid"):
        flash("Você não pode desativar o próprio usuário.")
        return redirect(url_for("usuarios"))
    c=db(); c.execute("UPDATE usuarios SET ativo=CASE WHEN COALESCE(ativo,1)=1 THEN 0 ELSE 1 END WHERE id=?",(id,)); c.commit(); c.close(); flash("Status do usuário atualizado."); return redirect(url_for("usuarios"))

@app.route("/usuarios/excluir/<int:id>", methods=["POST"])
@permission_required("admin")
def excluir_usuario(id):
    if id == session.get("uid"):
        flash("Você não pode excluir o próprio usuário.")
        return redirect(url_for("usuarios"))
    c=db(); c.execute("DELETE FROM usuarios WHERE id=?",(id,)); c.commit(); c.close(); flash("Usuário excluído."); return redirect(url_for("usuarios"))

@app.route("/despesas", methods=["GET", "POST"])
@login_required
def despesas():
    c=db(); d=request.args.get("data",date.today().isoformat())
    if request.method == "POST":
        descricao=request.form["descricao"].strip(); valor=request.form["valor"]; tipo=request.form.get("tipo","Variável"); data_lanc=request.form.get("data",d); recorrente=1 if request.form.get("recorrente") else 0
        c.execute("INSERT INTO despesas(descricao,valor,tipo,data,recorrente,observacoes) VALUES(?,?,?,?,?,?)",(descricao,valor,tipo,data_lanc,recorrente,request.form.get("observacoes",""))); c.commit(); flash("Despesa lançada."); c.close(); return redirect(url_for("despesas",data=data_lanc))
    rows=c.execute("SELECT * FROM despesas WHERE data=? OR (tipo='Fixa' AND recorrente=1 AND data<=?) ORDER BY data DESC,id DESC",(d,d)).fetchall()
    total=c.execute("SELECT COALESCE(SUM(valor),0) v FROM despesas WHERE data=? OR (tipo='Fixa' AND recorrente=1 AND data<=?)",(d,d)).fetchone()["v"]
    fixas=c.execute("SELECT * FROM despesas WHERE tipo='Fixa' AND recorrente=1 ORDER BY descricao").fetchall()
    c.close(); return render_template("despesas.html",rows=rows,total=total,fixas=fixas,data=d)

@app.route("/despesas/editar/<int:id>",methods=["GET","POST"])
@permission_required("edit")
def editar_despesa(id):
    c=db()
    if request.method=="POST":
        c.execute("UPDATE despesas SET descricao=?,valor=?,tipo=?,data=?,recorrente=?,observacoes=? WHERE id=?",(request.form["descricao"],request.form["valor"],request.form["tipo"],request.form["data"],1 if request.form.get("recorrente") else 0,request.form.get("observacoes",""),id)); c.commit(); c.close(); flash("Despesa atualizada."); return redirect(url_for("despesas",data=request.form["data"]))
    edit=c.execute("SELECT * FROM despesas WHERE id=?",(id,)).fetchone(); c.close(); return render_template("despesa_edit.html",edit=edit)

@app.route("/despesas/excluir/<int:id>",methods=["POST"])
@permission_required("edit")
def excluir_despesa(id):
    c=db(); c.execute("DELETE FROM despesas WHERE id=?",(id,)); c.commit(); c.close(); flash("Despesa excluída."); return redirect(url_for("despesas"))

# Área pública para o cliente agendar sem login
@app.route("/agendar",methods=["GET","POST"])
def publico():
    c=db()
    if request.method=="POST":
        nome,telefone,bar,ser,dt,hr=[request.form[x] for x in ("nome","telefone","barbeiro","servico","data","hora")]
        cli=c.execute("SELECT id FROM clientes WHERE telefone=?",(telefone,)).fetchone()
        if cli: cid=cli["id"]
        else:
            cur=c.execute("INSERT INTO clientes(nome,telefone) VALUES(?,?) RETURNING id",(nome,telefone)); cid=cur.fetchone()["id"]
        if c.execute("SELECT 1 FROM agendamentos WHERE barbeiro_id=? AND data=? AND hora=? AND status!='Cancelado'",(bar,dt,hr)).fetchone():
            flash("Esse horário acabou de ser ocupado. Escolha outro.")
        else:
            c.execute("INSERT INTO agendamentos(cliente_id,barbeiro_id,servico_id,data,hora,origem) VALUES(?,?,?,?,?,?)",(cid,bar,ser,dt,hr,"cliente")); c.commit(); flash("Agendamento solicitado com sucesso!")
            c.close(); return redirect(url_for("publico"))
    bars=c.execute("SELECT * FROM barbeiros WHERE ativo=1 ORDER BY nome").fetchall(); services=c.execute("SELECT * FROM servicos WHERE ativo=1 ORDER BY nome").fetchall(); c.close()
    return render_template("publico.html",barbeiros=bars,servicos=services)

@app.route("/api/horarios")
def horarios():
    bar=request.args.get("barbeiro"); dt=request.args.get("data")
    c=db(); used=[r["hora"] for r in c.execute("SELECT hora FROM agendamentos WHERE barbeiro_id=? AND data=? AND status!='Cancelado'",(bar,dt)).fetchall()]; c.close()
    return jsonify({"ocupados":used})

# Initialize the database when Gunicorn imports app:app.
init()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)

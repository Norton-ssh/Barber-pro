
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, os
from datetime import datetime, date
from functools import wraps

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
        c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios(id SERIAL PRIMARY KEY,nome TEXT,email TEXT UNIQUE,senha TEXT,papel TEXT DEFAULT 'admin');
        """)
        c.execute("""CREATE TABLE IF NOT EXISTS clientes(id SERIAL PRIMARY KEY,nome TEXT NOT NULL,telefone TEXT,email TEXT,aniversario TEXT,observacoes TEXT);""")
        c.execute("""CREATE TABLE IF NOT EXISTS barbeiros(id SERIAL PRIMARY KEY,nome TEXT NOT NULL,telefone TEXT,comissao REAL DEFAULT 40,ativo INTEGER DEFAULT 1);""")
        c.execute("""CREATE TABLE IF NOT EXISTS servicos(id SERIAL PRIMARY KEY,nome TEXT NOT NULL,duracao INTEGER DEFAULT 30,preco REAL DEFAULT 0,ativo INTEGER DEFAULT 1);""")
        c.execute("""CREATE TABLE IF NOT EXISTS agendamentos(id SERIAL PRIMARY KEY,cliente_id INTEGER,barbeiro_id INTEGER,servico_id INTEGER,data TEXT,hora TEXT,status TEXT DEFAULT 'Agendado',origem TEXT DEFAULT 'painel',observacoes TEXT);""")
        c.execute("""CREATE TABLE IF NOT EXISTS vendas(id SERIAL PRIMARY KEY,cliente_id INTEGER,barbeiro_id INTEGER,servico_id INTEGER,valor REAL,pagamento TEXT,data TEXT,hora TEXT,agendamento_id INTEGER);""")
    else:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,email TEXT UNIQUE,senha TEXT,papel TEXT DEFAULT 'admin');
        CREATE TABLE IF NOT EXISTS clientes(id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT NOT NULL,telefone TEXT,email TEXT,aniversario TEXT,observacoes TEXT);
        CREATE TABLE IF NOT EXISTS barbeiros(id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT NOT NULL,telefone TEXT,comissao REAL DEFAULT 40,ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS servicos(id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT NOT NULL,duracao INTEGER DEFAULT 30,preco REAL DEFAULT 0,ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS agendamentos(id INTEGER PRIMARY KEY AUTOINCREMENT,cliente_id INTEGER,barbeiro_id INTEGER,servico_id INTEGER,data TEXT,hora TEXT,status TEXT DEFAULT 'Agendado',origem TEXT DEFAULT 'painel',observacoes TEXT);
        CREATE TABLE IF NOT EXISTS vendas(id INTEGER PRIMARY KEY AUTOINCREMENT,cliente_id INTEGER,barbeiro_id INTEGER,servico_id INTEGER,valor REAL,pagamento TEXT,data TEXT,hora TEXT,agendamento_id INTEGER);
        """)
    if not c.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
        c.execute("INSERT INTO usuarios(nome,email,senha,papel) VALUES(?,?,?,?)",("Administrador","admin@vipbarbearia.com","123456","admin"))
    if not c.execute("SELECT 1 FROM servicos LIMIT 1").fetchone():
        rows=[("Corte",40,40),("Barba",30,30),("Corte + Barba",60,60),("Sobrancelha",15,15)]
        c.executemany("INSERT INTO servicos(nome,duracao,preco) VALUES(?,?,?)",rows)
    if not c.execute("SELECT 1 FROM barbeiros LIMIT 1").fetchone():
        c.executemany("INSERT INTO barbeiros(nome,comissao) VALUES(?,?)",[("Carlos",40),("Rafael",40)])
    c.commit(); c.close()

def login_required(f):
    @wraps(f)
    def w(*a,**k):
        if not session.get("uid"): return redirect(url_for("login"))
        return f(*a,**k)
    return w

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        c=db(); u=c.execute("SELECT * FROM usuarios WHERE email=? AND senha=?",(request.form["email"],request.form["senha"])).fetchone(); c.close()
        if u:
            session["uid"]=u["id"]; session["nome"]=u["nome"]; session["papel"]=u["papel"]
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
    prox=c.execute("""SELECT a.*,cl.nome cliente,b.nome barbeiro,s.nome servico,s.preco FROM agendamentos a
    LEFT JOIN clientes cl ON cl.id=a.cliente_id LEFT JOIN barbeiros b ON b.id=a.barbeiro_id
    LEFT JOIN servicos s ON s.id=a.servico_id WHERE a.data=? ORDER BY a.hora LIMIT 10""",(hoje,)).fetchall()
    c.close(); return render_template("dashboard.html",fat=fat,atend=atend,ag=ag,ticket=fat/atend if atend else 0,prox=prox,hoje=hoje)

@app.route("/clientes",methods=["GET","POST"])
@login_required
def clientes():
    c=db()
    if request.method=="POST":
        c.execute("INSERT INTO clientes(nome,telefone,email,aniversario,observacoes) VALUES(?,?,?,?,?)",
        (request.form["nome"],request.form.get("telefone",""),request.form.get("email",""),request.form.get("aniversario",""),request.form.get("observacoes",""))); c.commit(); flash("Cliente cadastrado.")
    rows=c.execute("SELECT * FROM clientes ORDER BY nome").fetchall(); c.close()
    return render_template("clientes.html",rows=rows)

@app.route("/barbeiros",methods=["GET","POST"])
@login_required
def barbeiros():
    c=db()
    if request.method=="POST":
        c.execute("INSERT INTO barbeiros(nome,telefone,comissao) VALUES(?,?,?)",(request.form["nome"],request.form.get("telefone",""),request.form.get("comissao",40))); c.commit(); flash("Barbeiro cadastrado.")
    rows=c.execute("SELECT * FROM barbeiros ORDER BY nome").fetchall(); c.close(); return render_template("barbeiros.html",rows=rows)

@app.route("/servicos",methods=["GET","POST"])
@login_required
def servicos():
    c=db()
    if request.method=="POST":
        c.execute("INSERT INTO servicos(nome,duracao,preco) VALUES(?,?,?)",(request.form["nome"],request.form.get("duracao",30),request.form.get("preco",0))); c.commit(); flash("Serviço cadastrado.")
    rows=c.execute("SELECT * FROM servicos ORDER BY nome").fetchall(); c.close(); return render_template("servicos.html",rows=rows)

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

@app.route("/agenda/status/<int:id>/<status>")
@login_required
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

@app.route("/relatorios")
@login_required
def relatorios():
    d=request.args.get("data",date.today().isoformat()); c=db()
    total=c.execute("SELECT COALESCE(SUM(valor),0) v FROM vendas WHERE data=?",(d,)).fetchone()["v"]
    formas=c.execute("SELECT pagamento, SUM(valor) total FROM vendas WHERE data=? GROUP BY pagamento",(d,)).fetchall()
    com=c.execute("""SELECT b.nome,SUM(v.valor) faturamento, b.comissao,
    SUM(v.valor)*b.comissao/100 comissao_valor FROM vendas v JOIN barbeiros b ON b.id=v.barbeiro_id WHERE v.data=? GROUP BY b.id""",(d,)).fetchall()
    serv=c.execute("""SELECT s.nome,COUNT(v.id) qtd,SUM(v.valor) total FROM vendas v JOIN servicos s ON s.id=v.servico_id WHERE v.data=? GROUP BY s.id ORDER BY total DESC""",(d,)).fetchall()
    c.close(); return render_template("relatorios.html",data=d,total=total,formas=formas,com=com,serv=serv)

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

if __name__=="__main__":
    init(); app.run(host="0.0.0.0",port=5000)

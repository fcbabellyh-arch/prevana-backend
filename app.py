from flask import Flask, request, jsonify, send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import os, uuid, json

app = Flask(__name__)

OR    = colors.HexColor('#C9A84C')
OR_CL = colors.HexColor('#E8C97A')
NOIR  = colors.HexColor('#0A0A0F')
ANTH  = colors.HexColor('#141420')
CARTE = colors.HexColor('#1A1A2E')
BORD  = colors.HexColor('#2A2A45')
BLANC = colors.HexColor('#F0EDE8')
GRIS  = colors.HexColor('#8A8AAA')
VERT  = colors.HexColor('#4CAF7D')
ROUGE = colors.HexColor('#E05A5A')

os.makedirs('/tmp/pdfs', exist_ok=True)

def fmt(n):
    try:
        return f"{float(n):,.0f} €".replace(",", " ")
    except:
        return "0 €"

def pct(r, p):
    try:
        return f"{round((float(r)/float(p)-1)*100, 1):+.1f}%"
    except:
        return "—"

def add_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(OR)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(18*mm, 12*mm, "prev")
    canvas.setFillColor(BLANC)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(18*mm + canvas.stringWidth("prev","Helvetica-Bold",9), 12*mm, "ana")
    canvas.setFillColor(GRIS)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawCentredString(A4[0]/2, 12*mm, f"Prévisionnel financier · {doc.title}")
    canvas.drawRightString(A4[0]-18*mm, 12*mm, f"Page {doc.page}")
    canvas.setStrokeColor(BORD)
    canvas.setLineWidth(0.4)
    canvas.line(18*mm, 16*mm, A4[0]-18*mm, 16*mm)
    canvas.restoreState()

def generate_pdf_classique(data):
    filename = f"/tmp/pdfs/{uuid.uuid4()}.pdf"
    nom      = data.get("nom", "Mon projet")
    secteur  = data.get("secteur", "—")
    forme    = data.get("forme_juridique", "—")
    duree    = int(data.get("duree", 3))
    ventes   = data.get("ventes", [])
    charges  = data.get("charges", [])
    rem_dir  = float(data.get("dirigeant_rem", 0))
    apport   = float(data.get("apport", 0))
    emprunt  = float(data.get("emprunt", 0))
    taux     = float(data.get("taux_emprunt", 3.5)) / 100
    duree_e  = int(data.get("duree_emprunt", 7))

    # Calculs CA
    ca_mensuel = sum(float(v.get("prix",0)) * float(v.get("qte",0)) for v in ventes)
    ca_an1     = ca_mensuel * 12
    croiss2    = float(data.get("croissance_an2", 20)) / 100
    croiss3    = float(data.get("croissance_an3", 20)) / 100
    ca_an2     = ca_an1 * (1 + croiss2)
    ca_an3     = ca_an2 * (1 + croiss3)

    # Calculs charges
    ch_mensuel = sum(float(c.get("montant",0)) for c in charges)
    ch_an1     = ch_mensuel * 12
    ch_an2     = ch_an1 * 1.05
    ch_an3     = ch_an2 * 1.05

    # Dirigeant
    cs_dir = rem_dir * 0.45 * 12

    # Emprunt mensualité
    if emprunt > 0 and taux > 0:
        n = duree_e * 12
        r = taux / 12
        mens = emprunt * r / (1 - (1+r)**(-n))
    else:
        mens = 0

    # Résultats
    res_an1 = ca_an1 - ch_an1 - rem_dir*12 - cs_dir
    res_an2 = ca_an2 - ch_an2 - rem_dir*12 - cs_dir
    res_an3 = ca_an3 - ch_an3 - rem_dir*12 - cs_dir

    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=20*mm, bottomMargin=22*mm,
        title=nom
    )

    S = {
        "titre": ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=22, textColor=BLANC, spaceAfter=4),
        "section": ParagraphStyle("s", fontName="Helvetica-Bold", fontSize=9, textColor=OR, spaceBefore=18, spaceAfter=8, textTransform="uppercase"),
        "body": ParagraphStyle("b", fontName="Helvetica", fontSize=9, textColor=BLANC, leading=14),
        "note": ParagraphStyle("n", fontName="Helvetica-Oblique", fontSize=8, textColor=GRIS, leading=12),
    }

    story = []

    # EN-TETE
    hdr = [[
        Paragraph(f"<font color='#C9A84C'><b>prev</b></font><font color='#F0EDE8'>ana</font>",
                  ParagraphStyle("logo", fontName="Helvetica-Bold", fontSize=20, textColor=BLANC)),
        Paragraph(f"<b>Prévisionnel Financier</b><br/><font color='#8A8AAA' size='9'>{nom}</font>",
                  ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=13, textColor=BLANC, alignment=TA_RIGHT))
    ]]
    t = Table(hdr, colWidths=[85*mm, 89*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),ANTH),
        ('ROWPADDING',(0,0),(-1,-1),14),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LINEBELOW',(0,0),(-1,-1),0.5,OR),
    ]))
    story.append(t)
    story.append(Spacer(1, 8*mm))

    # INFOS PROJET
    story.append(Paragraph("Informations sur le projet", S["section"]))
    info = [
        ["Nom du projet", nom],
        ["Secteur d'activité", secteur],
        ["Forme juridique", forme],
        ["Durée du prévisionnel", f"{duree} an(s)"],
    ]
    ti = Table(info, colWidths=[60*mm, 114*mm])
    ti.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(0,-1),CARTE),
        ('BACKGROUND',(1,0),(1,-1),ANTH),
        ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),
        ('FONTNAME',(1,0),(1,-1),'Helvetica'),
        ('FONTSIZE',(0,0),(-1,-1),9),
        ('TEXTCOLOR',(0,0),(0,-1),OR),
        ('TEXTCOLOR',(1,0),(1,-1),BLANC),
        ('ROWPADDING',(0,0),(-1,-1),7),
        ('GRID',(0,0),(-1,-1),0.3,BORD),
    ]))
    story.append(ti)
    story.append(Spacer(1, 6*mm))

    # COMPTE DE RÉSULTAT
    story.append(Paragraph("Compte de résultat prévisionnel", S["section"]))
    cr_data = [
        ["", "Année 1", "Année 2", "Année 3"],
        ["Chiffre d'affaires", fmt(ca_an1), fmt(ca_an2), fmt(ca_an3)],
        ["Charges d'exploitation", fmt(ch_an1), fmt(ch_an2), fmt(ch_an3)],
        ["Rémunération dirigeant", fmt(rem_dir*12), fmt(rem_dir*12), fmt(rem_dir*12)],
        ["Charges sociales dirigeant", fmt(cs_dir), fmt(cs_dir), fmt(cs_dir)],
        ["Résultat d'exploitation", fmt(res_an1), fmt(res_an2), fmt(res_an3)],
    ]
    tcr = Table(cr_data, colWidths=[65*mm, 38*mm, 38*mm, 33*mm])
    tcr.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),CARTE),
        ('TEXTCOLOR',(0,0),(-1,0),OR),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),
        ('FONTNAME',(1,1),(-1,-2),'Helvetica'),
        ('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,-1),9),
        ('TEXTCOLOR',(0,1),(0,-1),BLANC),
        ('TEXTCOLOR',(1,1),(-1,-2),GRIS),
        ('TEXTCOLOR',(0,-1),(-1,-1),OR),
        ('BACKGROUND',(0,-1),(-1,-1),CARTE),
        ('ROWPADDING',(0,0),(-1,-1),7),
        ('GRID',(0,0),(-1,-1),0.3,BORD),
        ('ROWBACKGROUNDS',(0,1),(-1,-2),[ANTH, CARTE]),
        ('ALIGN',(1,0),(-1,-1),'RIGHT'),
    ]))
    story.append(tcr)
    story.append(Spacer(1, 6*mm))

    # PLAN DE FINANCEMENT
    story.append(Paragraph("Plan de financement", S["section"]))
    total_invest = float(data.get("total_investissement", 0))
    pf_data = [
        ["Emplois", "", "Ressources", ""],
        ["Investissements", fmt(total_invest), "Apport personnel", fmt(apport)],
        ["Besoin en fonds de roulement", fmt(ch_mensuel*2), "Emprunt bancaire", fmt(emprunt)],
        ["Trésorerie de départ", fmt(float(data.get("treso_depart",0))), "", ""],
        ["TOTAL EMPLOIS", fmt(total_invest + ch_mensuel*2), "TOTAL RESSOURCES", fmt(apport+emprunt)],
    ]
    tpf = Table(pf_data, colWidths=[60*mm, 34*mm, 60*mm, 34*mm])
    tpf.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),CARTE),
        ('TEXTCOLOR',(0,0),(-1,0),OR),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,-1),9),
        ('TEXTCOLOR',(0,1),(-1,-2),BLANC),
        ('TEXTCOLOR',(0,-1),(-1,-1),OR),
        ('BACKGROUND',(0,-1),(-1,-1),CARTE),
        ('ROWPADDING',(0,0),(-1,-1),7),
        ('GRID',(0,0),(-1,-1),0.3,BORD),
        ('ROWBACKGROUNDS',(0,1),(-1,-2),[ANTH, CARTE]),
        ('ALIGN',(1,0),(1,-1),'RIGHT'),
        ('ALIGN',(3,0),(3,-1),'RIGHT'),
    ]))
    story.append(tpf)
    story.append(Spacer(1, 6*mm))

    # TRESORERIE MENSUELLE AN 1
    story.append(Paragraph("Plan de trésorerie — Année 1 (mensuel)", S["section"]))
    mois_noms = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]
    treso_data = [[""] + mois_noms]
    ca_row  = ["CA mensuel"]
    ch_row  = ["Charges"]
    sol_row = ["Solde mensuel"]
    cum_row = ["Tréso. cumulée"]
    cumul = float(data.get("treso_depart", 0))
    for i in range(12):
        ca_m  = ca_an1 / 12
        ch_m  = ch_mensuel + rem_dir + (cs_dir/12) + mens
        sol_m = ca_m - ch_m
        cumul += sol_m
        ca_row.append(fmt(ca_m))
        ch_row.append(fmt(ch_m))
        sol_row.append(fmt(sol_m))
        cum_row.append(fmt(cumul))
    treso_data += [ca_row, ch_row, sol_row, cum_row]
    col_w = [22*mm] + [12.5*mm]*12
    tt = Table(treso_data, colWidths=col_w)
    tt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),CARTE),
        ('TEXTCOLOR',(0,0),(-1,0),OR),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,-1),7),
        ('TEXTCOLOR',(0,1),(0,-1),BLANC),
        ('TEXTCOLOR',(1,1),(-1,-1),GRIS),
        ('ROWPADDING',(0,0),(-1,-1),5),
        ('GRID',(0,0),(-1,-1),0.3,BORD),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[ANTH, CARTE]),
        ('ALIGN',(1,0),(-1,-1),'RIGHT'),
    ]))
    story.append(tt)
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph(
        "Ce prévisionnel est généré automatiquement par Prevana. Il ne constitue pas un document comptable officiel.",
        S["note"]
    ))

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    return filename

@app.route('/')
def index():
    return jsonify({"status": "Prevana PDF API is running"})

def serve_html(filename):
    from flask import Response
    try:
        with open(f'/app/{filename}', 'r', encoding='utf-8') as f:
            return Response(f.read(), mimetype='text/html')
    except FileNotFoundError:
        return f'Page {filename} introuvable', 404

@app.route('/formulaire')
def formulaire(): return serve_html('prevana-formulaire.html')

@app.route('/dashboard')
def dashboard(): return serve_html('prevana-dashboard.html')

@app.route('/abonnement')
def abonnement(): return serve_html('prevana-abonnement.html')

@app.route('/profil')
def profil(): return serve_html('prevana-profil.html')

@app.route('/suivi')
def suivi(): return serve_html('prevana-suivi.html')

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        type_prev = data.get("type", "classique")
        if type_prev == "classique":
            filepath = generate_pdf_classique(data)
        else:
            filepath = generate_pdf_classique(data)
        file_id = os.path.basename(filepath)
        base_url = request.host_url.rstrip('/')
        pdf_url  = f"{base_url}/files/{file_id}"
        return jsonify({"pdf_url": pdf_url, "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/files/<filename>')
def serve_file(filename):
    filepath = f"/tmp/pdfs/{filename}"
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='application/pdf')
    return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

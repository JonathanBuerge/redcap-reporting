from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter
import io
import os

def create_overlay_pdf(patient_data, measurements):
    """
    Erstellt ein transparentes PDF, das nur die Texte an den richtigen Positionen enthält.
    """
    packet = io.BytesIO()
    # Wichtig: bottomup=True ist Standard (0,0 ist unten links)
    c = canvas.Canvas(packet, pagesize=A4)
    
    # --- HIER KOMMEN IHRE DATEN HIN ---
    # Format: c.drawString(x, y, text)
    # Ein A4 Blatt ist ca. 595 Punkte breit und 842 Punkte hoch.
    
    # 1. Header Daten (Beispiel-Koordinaten, müssen Sie anpassen!)
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, str(patient_data.get("ID", "")))      # ID
    c.drawString(100, 730, patient_data.get("Name", ""))          # Name
    c.drawString(100, 710, patient_data.get("Geburtsdatum", ""))  # Geburtsdatum

    # 2. Messwerte (Beispiel: Handkraft)
    # Angenommen, das Feld für "Handkraft Vorher" ist bei x=200, y=600
    c.setFont("Helvetica-Bold", 10)
    
    # Handkraft Werte
    c.drawString(200, 600, f"{measurements.get('handkraft_pre', 0)} kg")
    c.drawString(300, 600, f"{measurements.get('handkraft_post', 0)} kg")
    
    # Grüne Prozentzahl berechnen und einfärben
    c.setFillColor(colors.green)
    c.drawString(400, 600, "+12.5%")
    c.setFillColor(colors.black) # Zurück zu Schwarz für nächsten Text

    # ... Hier alle weiteren Koordinaten einfügen ...

    c.save()
    packet.seek(0)
    return packet

def merge_pdfs(template_path, output_path, patient_data, measurements):
    """Legt die generierten Daten über das Template."""
    
    # 1. Overlay im Speicher erstellen
    overlay_packet = create_overlay_pdf(patient_data, measurements)
    new_pdf = PdfReader(overlay_packet)
    
    # 2. Template lesen
    existing_pdf = PdfReader(open(template_path, "rb"))
    output = PdfWriter()

    # 3. Seite für Seite mergen (hier nur Seite 1)
    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)

    # 4. Speichern
    with open(output_path, "wb") as outputStream:
        output.write(outputStream)

# --- TEST ---
if __name__ == "__main__":
    # Dummy Daten
    p_data = {"ID": "123", "Name": "Max Muster", "Geburtsdatum": "01.01.2010"}
    m_data = {"handkraft_pre": 14.6, "handkraft_post": 25.1}
    
    # Sie müssen eine Datei 'template.pdf' im Ordner haben!
    # (Erstellen Sie diese z.B. in Word/InDesign und speichern als PDF)
    if os.path.exists("template.pdf"):
        merge_pdfs("template.pdf", "finaler_report.pdf", p_data, m_data)
        print("PDF erstellt!")
    else:
        print("Fehler: Bitte legen Sie erst eine 'template.pdf' ab.")
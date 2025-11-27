import os
import math
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
from gtts import gTTS

# -------- helpers --------
def extract_text_from_pdf(path):
    doc = fitz.open(path)
    texts = []
    for page in doc:
        txt = page.get_text("text")
        if txt and txt.strip():
            texts.append(txt)
    return "\n\n".join(texts)

def chunk_text(text, max_chars=4500):
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        # try to break at last sentence end within window
        window = text[start:end]
        sep_pos = max(window.rfind(". "), window.rfind("\n\n"), window.rfind("! "), window.rfind("? "))
        if sep_pos == -1 or sep_pos < int(max_chars*0.5):
            sep_pos = max_chars
        chunks.append(text[start:start+sep_pos+1].strip())
        start += sep_pos+1
    return chunks

def save_as_mp3_gtts(text, out_path, lang="en"):
    chunks = chunk_text(text)
    temp_files = []
    try:
        for i, chunk in enumerate(chunks):
            tts = gTTS(text=chunk, lang=lang, slow=False)
            part = f"{out_path}.part{i}.mp3"
            tts.save(part)
            temp_files.append(part)
        # If only one chunk, rename
        if len(temp_files) == 1:
            os.replace(temp_files[0], out_path)
        else:
            # merge by concatenation (binary) - works for MP3 if same encoding; otherwise recommend ffmpeg externally.
            with open(out_path, "wb") as outfile:
                for fname in temp_files:
                    with open(fname, "rb") as infile:
                        outfile.write(infile.read())
    finally:
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

# -------- GUI --------
class PDFtoAudiobookApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF → Audiobook")
        self.geometry("520x260")
        self.pdf_path = None
        self.out_path = None

        tk.Label(self, text="PDF to Audiobook Converter", font=("Arial", 14, "bold")).pack(pady=8)

        frame = tk.Frame(self)
        frame.pack(pady=6, fill="x", padx=12)

        self.file_label = tk.Label(frame, text="No file selected", anchor="w")
        self.file_label.pack(side="left", fill="x", expand=True)

        tk.Button(frame, text="Choose PDF", command=self.choose_pdf).pack(side="right")

        out_frame = tk.Frame(self)
        out_frame.pack(padx=12, pady=6, fill="x")
        tk.Label(out_frame, text="Output MP3 name:").pack(side="left")
        self.out_entry = tk.Entry(out_frame)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.out_entry.insert(0, "audiobook.mp3")

        options_frame = tk.Frame(self)
        options_frame.pack(padx=12, fill="x")
        tk.Label(options_frame, text="Language (gTTS):").pack(side="left")
        self.lang_entry = tk.Entry(options_frame, width=6)
        self.lang_entry.pack(side="left", padx=6)
        self.lang_entry.insert(0, "en")

        self.convert_btn = tk.Button(self, text="Convert to MP3", command=self.start_conversion, width=20)
        self.convert_btn.pack(pady=12)

        self.status = tk.Label(self, text="Ready", anchor="w")
        self.status.pack(fill="x", padx=12)

    def choose_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.pdf_path = path
            self.file_label.config(text=os.path.basename(path))

    def start_conversion(self):
        if not self.pdf_path:
            messagebox.showerror("Error", "Please choose a PDF file first.")
            return
        out_name = self.out_entry.get().strip()
        if not out_name:
            messagebox.showerror("Error", "Please provide an output filename.")
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".mp3", initialfile=out_name,
                                                filetypes=[("MP3 audio", "*.mp3")])
        if not out_path:
            return
        self.out_path = out_path
        self.convert_btn.config(state="disabled")
        self.status.config(text="Extracting text...")
        threading.Thread(target=self._convert_worker, daemon=True).start()

    def _convert_worker(self):
        try:
            text = extract_text_from_pdf(self.pdf_path)
            if not text or not text.strip():
                self._set_status("No extractable text found in PDF.")
                self.convert_btn.config(state="normal")
                return
            self._set_status("Converting to speech (gTTS)...")
            save_as_mp3_gtts(text, self.out_path, lang=self.lang_entry.get().strip() or "en")
            self._set_status(f"Saved: {self.out_path}")
            messagebox.showinfo("Done", f"Audio saved to:\n{self.out_path}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{e}")
            self._set_status("Error")
        finally:
            self.convert_btn.config(state="normal")

    def _set_status(self, txt):
        self.status.config(text=txt)

if __name__ == "__main__":
    app = PDFtoAudiobookApp()
    app.mainloop()

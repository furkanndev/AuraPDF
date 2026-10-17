"""
AuraPDF - AI Belge Asistani ve Zeka Motoru (AI Document Intelligence Engine)
=============================================================================
Bu modül, PDF belgelerinin yerel (çevrimdisi/gizli) ve opsiyonel Google Gemini API
entegrasyonuyla analiz edilmesini, özetlenmesini, risk/tarih/tutar çikarimini ve
belge içi soru-cevap (Q&A) sohbet yeteneklerini saglar.
"""

import os
import re
import json
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any
from collections import Counter

import pymupdf as fitz
from PyQt6.QtCore import QThread, pyqtSignal, QSettings


class LocalDocumentIntelligence:
    """
    Yerel ve 100% Gizli Belge Analiz Motoru.
    Harici API anahtari veya internet baglantisi gerektirmeden belgeleri
    hizlica analiz eder, özet çikarir ve kritik maddeleri tespit eder.
    """

    # Hukuki, finansal ve operasyonel risk anahtar kelimeleri
    RISK_PATTERNS_TR = [
        ("cezai_sart", r"(cezai şart|tazminat|gecikme faizi|müeyyide|para cezası)", "Cezai Şart & Tazminat"),
        ("fesih", r"(fesih|haklı nedenle fesih|tek taraflı fesih|sözleşmenin sonu)", "Fesih & İptal Koşulları"),
        ("sorumluluk", r"(sorumluluk|kusur|zarar|rücu|müteselsil)", "Sorumluluk & Yükümlülük"),
        ("gizlilik", r"(gizlilik|sır saklama|üçüncü kişi|ifşa|kvkk)", "Gizlilik & Bilgi Güvenliği"),
        ("mucbir_sebep", r"(mücbir sebep|doğal afet|harp|olağanüstü hal)", "Mücbir Sebepler"),
        ("garanti", r"(garanti süresi|taahhüt|ayıp|kusurlu ifa)", "Garanti & Taahhütler"),
        ("yetkili_mahkeme", r"(yetkili mahkeme|icra dairesi|uyuşmazlık|tahkim)", "Uyuşmazlık & Yetki"),
    ]

    RISK_PATTERNS_EN = [
        ("liability", r"(liability|indemnif|damages|penalty|breach)", "Liability & Indemnity"),
        ("termination", r"(terminat|cancel|expire|forfeit)", "Termination Clauses"),
        ("confidentiality", r"(confidential|non-disclosure|proprietary|nda)", "Confidentiality"),
        ("force_majeure", r"(force majeure|act of god|unforeseen)", "Force Majeure"),
        ("warranty", r"(warrant|guarantee|defect|remedy)", "Warranty & Remedy"),
        ("jurisdiction", r"(jurisdiction|arbitration|governing law|dispute)", "Governing Law"),
    ]

    @classmethod
    def extract_document_text(cls, doc_path: str, max_pages: int = 150) -> Dict[str, Any]:
        """PDF belgesinin metnini sayfa sayfa ayiklar ve temel istatistikleri çikarir."""
        if not doc_path or not os.path.exists(doc_path):
            raise FileNotFoundError(f"Belge bulunamadi: {doc_path}")

        doc = fitz.open(doc_path)
        page_texts: Dict[int, str] = {}
        total_pages = len(doc)
        full_text_parts = []

        scan_pages = min(total_pages, max_pages)
        for pno in range(scan_pages):
            page = doc[pno]
            txt = page.get_text("text").strip()
            page_texts[pno + 1] = txt
            if txt:
                full_text_parts.append(txt)

        doc.close()

        full_text = "\n\n".join(full_text_parts)
        words = re.findall(r"\b\w+\b", full_text)
        word_count = len(words)
        reading_time_min = max(1, round(word_count / 200))

        return {
            "total_pages": total_pages,
            "scanned_pages": scan_pages,
            "word_count": word_count,
            "reading_time_min": reading_time_min,
            "page_texts": page_texts,
            "full_text": full_text,
            "has_text": word_count > 30,
        }

    @classmethod
    def generate_executive_summary(cls, doc_info: Dict[str, Any], lang: str = "tr") -> Dict[str, Any]:
        """Belgenin temel basliklarini ve en kritik cümlelerini çikararak yönetici özeti olusturur."""
        page_texts = doc_info.get("page_texts", {})
        full_text = doc_info.get("full_text", "")
        word_count = doc_info.get("word_count", 0)

        if not doc_info.get("has_text", False):
            if lang == "tr":
                return {
                    "overview": "Bu belge taranmış veya resim ağırlıklı bir PDF görünümündedir. Metin katmanı doğrudan okunabilir metin içermiyor. AuraPDF'in 'OCR Metin Tanıma' aracını kullanarak metin katmanı oluşturabilirsiniz.",
                    "key_takeaways": ["Metin katmanı bulunamadı", "OCR işlemi önerilir"],
                    "sections": []
                }
            else:
                return {
                    "overview": "This document appears to be scanned or image-based without an embedded text layer. You can use AuraPDF's OCR tool to generate a searchable text layer.",
                    "key_takeaways": ["No selectable text found", "OCR conversion recommended"],
                    "sections": []
                }

        # Cümleleri ayir
        sentences = re.split(r"(?<=[.!?])\s+", full_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 35 and len(s.strip()) < 350]

        # Kelime frekans puanlamasi
        words = [w.lower() for w in re.findall(r"\b\w{4,}\b", full_text)]
        word_freq = Counter(words)

        scored_sentences = []
        for s in sentences:
            score = sum(word_freq.get(w.lower(), 0) for w in re.findall(r"\b\w{4,}\b", s))
            scored_sentences.append((score, s))

        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        top_sentences = [s for _, s in scored_sentences[:6]]

        # Sayfa bazli özet/basliklar
        sections = []
        for pno, ptxt in sorted(page_texts.items()):
            lines = [l.strip() for l in ptxt.splitlines() if l.strip()]
            if lines:
                heading = lines[0][:80]
                sections.append({
                    "page": pno,
                    "heading": heading,
                    "preview": " ".join(lines[1:4])[:140] if len(lines) > 1 else heading
                })

        if lang == "tr":
            overview = (
                f"Bu belge toplam {doc_info.get('total_pages', 0)} sayfa ve yaklaşık {word_count:,} kelimeden oluşmaktadır. "
                f"Tahmini okuma süresi {doc_info.get('reading_time_min', 1)} dakikadır. "
                f"Belge içeriği aşağıda öne çıkan temel maddeler ve bölüm dağılımıyla özetlenmiştir."
            )
        else:
            overview = (
                f"This document contains {doc_info.get('total_pages', 0)} pages and approximately {word_count:,} words. "
                f"Estimated reading time is {doc_info.get('reading_time_min', 1)} minutes. "
                f"The core content is highlighted below with key takeaways and sectional distribution."
            )

        return {
            "overview": overview,
            "key_takeaways": top_sentences[:5] if top_sentences else ["Belge metni başarıyla işlendi."],
            "sections": sections[:10]
        }

    @classmethod
    def extract_risks_and_clauses(cls, doc_info: Dict[str, Any], lang: str = "tr") -> Dict[str, Any]:
        """Tarihleri, parasal tutarlari ve kritik yükümlülük maddelerini ayiklar."""
        page_texts = doc_info.get("page_texts", {})
        dates_found = []
        amounts_found = []
        risks_found = []

        patterns = cls.RISK_PATTERNS_TR if lang == "tr" else cls.RISK_PATTERNS_EN

        # Tarih regex'leri
        date_regex = re.compile(
            r"\b(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}|\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}|\b\d+\s+(?:gün|ay|yıl|days|months|years))\b",
            re.IGNORECASE
        )

        # Para tutari regex'i
        money_regex = re.compile(
            r"\b((?:[₺$€£]|TL|USD|EUR)\s*[\d.,]+|[\d.,]+\s*(?:TL|USD|EUR|Türk Lirası|Dolar|Euro))\b",
            re.IGNORECASE
        )

        seen_dates = set()
        seen_amounts = set()

        for pno, ptxt in page_texts.items():
            sentences = re.split(r"(?<=[.!?])\s+", ptxt)

            for s in sentences:
                s_clean = s.strip()
                if not s_clean or len(s_clean) < 15:
                    continue

                # Tarih arama
                for match in date_regex.finditer(s_clean):
                    val = match.group(0).strip()
                    if val not in seen_dates and len(val) >= 4:
                        seen_dates.add(val)
                        dates_found.append({
                            "value": val,
                            "context": s_clean[:140],
                            "page": pno
                        })

                # Para tutari arama
                for match in money_regex.finditer(s_clean):
                    val = match.group(0).strip()
                    if val not in seen_amounts and len(val) >= 2:
                        seen_amounts.add(val)
                        amounts_found.append({
                            "value": val,
                            "context": s_clean[:140],
                            "page": pno
                        })

                # Risk / Koşul arama
                for cat_id, cat_pattern, cat_title in patterns:
                    if re.search(cat_pattern, s_clean, re.IGNORECASE):
                        if len(risks_found) < 25:
                            risks_found.append({
                                "category": cat_title,
                                "clause": s_clean[:180],
                                "page": pno
                            })
                        break

        return {
            "dates": dates_found[:12],
            "amounts": amounts_found[:12],
            "risks": risks_found[:15]
        }

    @classmethod
    def answer_document_query(cls, query: str, doc_info: Dict[str, Any], lang: str = "tr") -> str:
        """Kullanicinin sorusuna belge içeriginden alinti yaparak yerel cevap üretir."""
        if not query.strip():
            return "Lütfen belgeye dair bir soru yazın." if lang == "tr" else "Please ask a question about the document."

        page_texts = doc_info.get("page_texts", {})
        q_tokens = [w.lower() for w in re.findall(r"\b\w{3,}\b", query)]

        if not q_tokens:
            return "Soru için yeterli anahtar kelime bulunamadı." if lang == "tr" else "Not enough keywords in query."

        matches = []
        for pno, ptxt in page_texts.items():
            sentences = re.split(r"(?<=[.!?])\s+", ptxt)
            for s in sentences:
                s_lower = s.lower()
                score = sum(1 for tok in q_tokens if tok in s_lower)
                if score > 0:
                    matches.append((score, pno, s.strip()))

        matches.sort(key=lambda x: x[0], reverse=True)

        if not matches:
            if lang == "tr":
                return f"'{query}' sorusuyla doğrudan eşleşen bir madde belgede bulunamadı. Lütfen farklı anahtar sözcüklerle sormayı deneyin."
            else:
                return f"No direct matches found in the document for '{query}'. Try asking with alternative terms."

        top_matches = matches[:3]
        if lang == "tr":
            ans_parts = ["Belgede tespit edilen ilgili maddeler:\n"]
            for score, pno, snippet in top_matches:
                ans_parts.append(f"• [Sayfa {pno}]: \"{snippet}\"\n")
            ans_parts.append("\n(Bu yanıt yerel belge zekası motoru tarafından belgenizden çıkarılmıştır.)")
            return "\n".join(ans_parts)
        else:
            ans_parts = ["Relevant excerpts found in the document:\n"]
            for score, pno, snippet in top_matches:
                ans_parts.append(f"• [Page {pno}]: \"{snippet}\"\n")
            ans_parts.append("\n(This answer was extracted locally from your document.)")
            return "\n".join(ans_parts)


class GeminiApiClient:
    """
    Google Gemini REST API Entegrasyonu.
    Harici kutuphane gerektirmeden standart Python urllib ile çalısır.
    """

    @classmethod
    def get_api_key(cls) -> str:
        """Kayıtlı Gemini API anahtarını QSettings veya ortam değişkeninden okur."""
        key = QSettings("AuraPDF", "AI").value("gemini_api_key", "", type=str)
        if not key:
            key = os.getenv("GEMINI_API_KEY", "")
        return key.strip()

    @classmethod
    def set_api_key(cls, key: str):
        """Gemini API anahtarını güvenli şekilde kaydeder."""
        QSettings("AuraPDF", "AI").setValue("gemini_api_key", key.strip())

    @classmethod
    def call_gemini(cls, prompt: str, system_instruction: str = "", model: str = "gemini-2.5-flash") -> str:
        """Gemini API'sine REST çağrısı yapar ve yanıt metnini döndürür."""
        api_key = cls.get_api_key()
        if not api_key:
            raise ValueError("Gemini API key is not configured.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                candidates = resp_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                return "Boş yanıt alındı."
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            raise RuntimeError(f"Gemini API Hatası ({e.code}): {err_body}")
        except Exception as e:
            raise RuntimeError(f"Bağlantı hatası: {str(e)}")


class AuraAiWorker(QThread):
    """
    Belge analizi ve yapay zeka işlemlerini arka planda yürüten iş parçacığı.
    UI kilitlenmelerini kesin olarak önler.
    """
    progressChanged = pyqtSignal(int, str)
    analysisFinished = pyqtSignal(dict)
    chatFinished = pyqtSignal(str)
    errorOccurred = pyqtSignal(str)

    def __init__(
        self,
        task_type: str,  # "analyze" | "chat"
        doc_path: str,
        query: str = "",
        doc_info: Optional[Dict[str, Any]] = None,
        lang: str = "tr",
        parent=None
    ):
        super().__init__(parent)
        self.task_type = task_type
        self.doc_path = doc_path
        self.query = query
        self.doc_info = doc_info
        self.lang = lang
        self._is_aborted = False

    def abort(self):
        self._is_aborted = True

    def run(self):
        try:
            if self.task_type == "analyze":
                self._run_analyze()
            elif self.task_type == "chat":
                self._run_chat()
        except Exception as e:
            if not self._is_aborted:
                self.errorOccurred.emit(str(e))

    def _run_analyze(self):
        self.progressChanged.emit(10, "Belge sayfaları taranıyor...")
        if self._is_aborted:
            return

        doc_info = LocalDocumentIntelligence.extract_document_text(self.doc_path)
        self.progressChanged.emit(40, "Metin katmanı çözümleniyor...")
        if self._is_aborted:
            return

        self.progressChanged.emit(60, "Yönetici özeti ve ana maddeler çıkarılıyor...")
        summary = LocalDocumentIntelligence.generate_executive_summary(doc_info, lang=self.lang)
        if self._is_aborted:
            return

        self.progressChanged.emit(85, "Kritik riskler, tarihler ve tutarlar tespit ediliyor...")
        risks_data = LocalDocumentIntelligence.extract_risks_and_clauses(doc_info, lang=self.lang)
        if self._is_aborted:
            return

        # Gemini API anahtarı varsa daha derin zeka özetini sorgula
        gemini_summary = None
        if GeminiApiClient.get_api_key() and doc_info.get("has_text", False):
            try:
                self.progressChanged.emit(90, "Google Gemini AI ile derin analiz yapılıyor...")
                prompt = (
                    f"Aşağıdaki PDF metnini incele ve profesyonel bir yönetici özeti çıkar. "
                    f"Belgenin amacını, en önemli 3-5 maddesini ve varsa kritik riskleri belirt:\n\n"
                    f"{doc_info['full_text'][:7000]}"
                )
                gemini_summary = GeminiApiClient.call_gemini(
                    prompt,
                    system_instruction="Sen profesyonel, objektif ve güvenilir bir PDF Belge Analiz Asistanısın. Türkçe yanıt ver."
                )
            except Exception:
                # Gemini başarısız olursa yerel analiz kusursuz çalışmaya devam eder
                pass

        self.progressChanged.emit(100, "Analiz tamamlandı!")

        result = {
            "doc_info": doc_info,
            "summary": summary,
            "risks_data": risks_data,
            "gemini_summary": gemini_summary,
            "is_gemini_active": bool(gemini_summary)
        }
        self.analysisFinished.emit(result)

    def _run_chat(self):
        self.progressChanged.emit(30, "Soru analiz ediliyor...")
        if self._is_aborted:
            return

        # 1. Gemini etkinse doğrudan sor
        api_key = GeminiApiClient.get_api_key()
        if api_key and self.doc_info and self.doc_info.get("has_text", False):
            try:
                self.progressChanged.emit(60, "Gemini AI yanıt hazırlıyor...")
                prompt = (
                    f"Belge İçeriği (Özet Kesit):\n{self.doc_info['full_text'][:7000]}\n\n"
                    f"Kullanıcı Sorusu: {self.query}\n\n"
                    f"Lütfen yalnızca belge içeriğine sadık kalarak, net, doğru ve yardımcı bir yanıt ver."
                )
                ans = GeminiApiClient.call_gemini(
                    prompt,
                    system_instruction="Sen AuraPDF Belge Asistanısın. Belgeye dayalı kesin ve nazik yanıtlar ver."
                )
                self.progressChanged.emit(100, "Tamamlandı!")
                self.chatFinished.emit(ans)
                return
            except Exception as e:
                # API hatası olursa yerel motor devreye girer
                pass

        # 2. Yerel Akıllı Motor
        self.progressChanged.emit(70, "Belge içinde anlamsal eşleşmeler aranıyor...")
        ans = LocalDocumentIntelligence.answer_document_query(
            self.query,
            self.doc_info or {},
            lang=self.lang
        )
        self.progressChanged.emit(100, "Tamamlandı!")
        self.chatFinished.emit(ans)

"""
AuraPDF Hyperlink and Entity Detector
====================================
Metin kutularında otomatik URL / Web Sitesi, E-Posta, Telefon Numarası
ve T.C. Kimlik Numarası tanıma ve işleme yardımcı modülü.
"""

import re


def is_valid_tc(tc_str: str) -> bool:
    """T.C. Kimlik Numarası algoritma doğrulaması."""
    if not tc_str or len(tc_str) != 11 or not tc_str.isdigit() or tc_str[0] == '0':
        return False
    digits = [int(c) for c in tc_str]
    d_odd = sum(digits[0:9:2])   # 1, 3, 5, 7, 9. haneler
    d_even = sum(digits[1:8:2])  # 2, 4, 6, 8. haneler
    d10 = ((d_odd * 7) - d_even) % 10
    if digits[9] != d10:
        return False
    d11 = sum(digits[:10]) % 10
    return digits[10] == d11


# Regex Desenleri
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')

URL_REGEX = re.compile(
    r'(?:https?://[^\s<>"\'\)]+|www\.[^\s<>"\'\)]+|(?:[a-zA-Z0-9-]+\.)+(?:com\.tr|gov\.tr|edu\.tr|org\.tr|net\.tr|bel\.tr|k12\.tr|av\.tr|com|org|net|gov|edu|io|ai|me|info|biz|xyz|app|dev)(?:/[^\s<>"\'\)]*)?)',
    re.IGNORECASE
)

TC_LABEL_REGEX = re.compile(r'(?i)(?:t\.?c\.?(?:\s*kimlik)?(?:\s*no)?|tckn|kimlik\s*no)[\s:]*([1-9]\d{10})\b')
TC_DIGITS_REGEX = re.compile(r'\b[1-9]\d{10}\b')

PHONE_REGEX = re.compile(
    r'(?:'
    r'(?:\+90|0090)\s*(?:\([1-9]\d{2}\)|[1-9]\d{2})[\s\.\-]?\d{3}[\s\.\-]?\d{2}[\s\.\-]?\d{2}'
    r'|\(?0\s*[1-9]\d{2}\)?[\s\.\-]\d{3}[\s\.\-]?\d{2}[\s\.\-]?\d{2}'
    r'|\b5\d{2}[\s\.\-]\d{3}[\s\.\-]?\d{2}[\s\.\-]?\d{2}\b'
    r'|\b444\s*\d{1}\s*\d{3}\b'
    r'|\b0?850\s*\d{3}[\s\.\-]?\d{2}[\s\.\-]?\d{2}\b'
    r'|\+\d{1,4}(?:[\s\.\-]?\(?\d{1,4}\)?){1,4}[\s\.\-]?\d{2,4}'
    r')'
)


def detect_hyperlink(text: str) -> dict | None:
    """
    Verilen metin içindeki bağlantı / varlığı (URL, E-Posta, Telefon, TC Kimlik) tespit eder.
    Tespit edilen türe göre zengin metadata ve yönlendirme linki döndürür.
    Dümdüz ardışık sayılar asla bağlantı olarak algılanmaz.
    """
    if not text:
        return None
    content = text.strip()

    # 0. Düz ardışık sayılar (örn. 123456, 12345678901, 5551234567 vb.) asla link veya TC olarak algılanmamalıdır.
    pure_digits = re.sub(r'[\s\.\,\-_/]+', '', content)
    if pure_digits.isdigit() and not content.startswith('+'):
        # Eğer açık bir "TC:" veya "TCKN" etiketi yoksa düz sayıyı yoksay
        if not TC_LABEL_REGEX.search(content):
            return None

    # 1. E-Posta Tespiti
    m_email = EMAIL_REGEX.search(content)
    if m_email:
        raw = m_email.group(0)
        return {
            'type': 'email',
            'url': f'mailto:{raw}',
            'raw': raw,
            'title': 'E-Posta',
            'icon': '',
            'tooltip': f'E-Posta: {raw}\n(Tıklayarak e-posta gönderin, sağ tık ile kopyalayın)'
        }

    # 2. Web Sitesi / URL Tespiti
    m_url = URL_REGEX.search(content)
    if m_url:
        raw = m_url.group(0).rstrip('.,;:)')
        url = raw
        if url.startswith('www.'):
            url = 'https://' + url
        elif not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return {
            'type': 'url',
            'url': url,
            'raw': raw,
            'title': 'Web Sitesi',
            'icon': '',
            'tooltip': f'Web Sitesi: {url}\n(Tıklayarak tarayıcıda açın, sağ tık ile kopyalayın)'
        }

    # 3. T.C. Kimlik Numarası Tespiti (Sadece açıkça TC etiketi varsa ve algoritması doğrulanmışsa)
    m_tc_lbl = TC_LABEL_REGEX.search(content)
    if m_tc_lbl:
        raw = m_tc_lbl.group(1)
        if is_valid_tc(raw):
            return {
                'type': 'tc',
                'url': '',
                'raw': raw,
                'title': 'T.C. Kimlik No',
                'icon': '',
                'tooltip': f'T.C. Kimlik No: {raw}\n(Tıklayarak panoya kopyalayın)'
            }

    # 4. Telefon Numarası Tespiti
    m_phone = PHONE_REGEX.search(content)
    if m_phone:
        raw = m_phone.group(0).strip()
        clean = re.sub(r'[\s\(\)\-\.]', '', raw)
        if clean.startswith('+'):
            tel_url = f'tel:{clean}'
        elif clean.startswith('0'):
            tel_url = f'tel:{clean}'
        elif len(clean) == 10 and clean.startswith('5'):
            tel_url = f'tel:+90{clean}'
        else:
            tel_url = f'tel:{clean}'
        return {
            'type': 'phone',
            'url': tel_url,
            'raw': raw,
            'clean': clean,
            'title': 'Telefon',
            'icon': '',
            'tooltip': f'Telefon: {raw}\n(Aramak için tıklayın, sağ tık ile kopyalayın)'
        }

    return None

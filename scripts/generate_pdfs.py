#!/usr/bin/env python3
"""Regenerate the two synthetic one-page packing lists (reportlab required)."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'sample-data'


def generate(filename: str, title: str, reference: str, rows: list[tuple[str, str, int]], note: str):
    destination = FIXTURES / filename
    c = canvas.Canvas(str(destination), pagesize=A4, pageCompression=0)
    c.setTitle(title)
    c.setAuthor('ParcelProof synthetic fixture generator')
    w, h = A4
    ink = colors.HexColor('#173136')
    teal = colors.HexColor('#18796D')
    muted = colors.HexColor('#526767')
    c.setFillColor(ink)
    c.rect(0, h-130, w, 130, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(44, h-43, 'PARCELPROOF / SYNTHETIC TEST DATA')
    c.setFont('Helvetica-Bold', 25)
    c.drawString(44, h-82, 'Packing list')
    c.setFont('Helvetica', 10)
    c.drawString(44, h-104, reference)
    c.setFillColor(ink)
    c.setFont('Helvetica-Bold', 13)
    c.drawString(44, h-171, title)
    c.setFillColor(muted)
    c.setFont('Helvetica', 10)
    c.drawString(44, h-193, 'One page / text PDF / 3 line items')
    c.setFillColor(teal)
    c.rect(44, h-248, w-88, 30, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(57, h-238, 'SKU | Product label | Quantity')
    y = h-285
    for i, (sku, label, qty) in enumerate(rows):
        c.setFillColor(colors.HexColor('#F0F5F2') if i % 2 == 0 else colors.white)
        c.rect(44, y-16, w-88, 44, fill=1, stroke=0)
        c.setFillColor(ink)
        c.setFont('Helvetica', 12)
        c.drawString(57, y, f'{sku} | {label} | {qty}')
        y -= 44
    c.setStrokeColor(colors.HexColor('#D8E2DD'))
    c.line(44, y+18, w-44, y+18)
    c.setFillColor(ink)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(44, y-24, 'Fixture purpose')
    c.setFillColor(muted)
    c.setFont('Helvetica', 10)
    for j, line in enumerate(note.split('\n')):
        c.drawString(44, y-47-j*16, line)
    c.setFont('Helvetica', 9)
    c.drawString(44, 72, 'Generated for a small controlled PoC. No real order or customer information.')
    c.drawString(44, 56, 'Use stable ITEM markers in photos; an invisible label is not proof of missing stock.')
    c.drawRightString(w-44, 33, '1 / 1')
    c.save()
    return destination

if __name__ == '__main__':
    FIXTURES.mkdir(parents=True, exist_ok=True)
    generate('packing_list_correct.pdf', 'Correct manifest', 'Test order: SYNTH-001 / fixture A', [
        ('TEA-101', 'Green Tea', 2),
        ('TEA-102', 'Green Tea Decaf', 1),
        ('MUG-201', 'Ceramic Mug', 1),
    ], 'Expected contents of the corrected delivery image.\nAlso compare against the issue-delivery photos to reveal discrepancies.')
    generate('packing_list_incorrect.pdf', 'Intentionally incorrect manifest', 'Test order: SYNTH-001 / fixture B', [
        ('TEA-101', 'Green Tea', 1),
        ('TEA-102', 'Green Tea Decaf', 1),
        ('MUG-202', 'Travel Mug', 1),
    ], 'This is a valid PDF with deliberately wrong order contents.\nIt understates Green Tea quantity and requests the wrong mug SKU.')
    print('Generated exactly two one-page text PDF fixtures.')

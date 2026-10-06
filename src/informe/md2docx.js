// Convierte informes/informe_final.md (subconjunto de Markdown) en un .docx con formato académico.
// Uso: node md2docx.js <entrada.md> <salida.docx>
// El índice queda como campo vacío; actualizar_indice.ps1 lo rellena con Word y guarda el archivo.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, ImageRun, Footer, PageNumber, TableOfContents, PageBreak,
  LevelFormat,
} = require("docx");

const [entrada, salida] = process.argv.slice(2);
const base = path.dirname(path.resolve(entrada));
// Une las líneas cortadas a mano: un párrafo (o un elemento de lista o de cita) que sigue en la
// línea siguiente forma un solo párrafo, como en Markdown.
const MARCA = /^(#|\||!\[|-\s|\d+\.\s|---$)/;
const lineas = [];
for (const l of fs.readFileSync(entrada, "utf8").replace(/\r/g, "").split("\n")) {
  const previa = lineas[lineas.length - 1];
  if (previa !== undefined && previa.trim() && l.trim()) {
    const enCita = l.startsWith(">") && previa.startsWith(">");
    const c = l.replace(/^> ?/, "");
    const pc = previa.replace(/^> ?/, "");
    if (enCita && pc.trim() && c.trim() && !MARCA.test(c.trim())) {
      lineas[lineas.length - 1] = previa + " " + c.trim();
      continue;
    }
    if (!l.startsWith(">") && !previa.startsWith(">") && !/^(#|\||!\[)/.test(previa.trim()) && !MARCA.test(l.trim())) {
      lineas[lineas.length - 1] = previa + " " + l.trim();
      continue;
    }
  }
  lineas.push(l);
}

const ANCHO = 9070; // A4 con márgenes de 2,5 cm, en DXA
const FUENTE = "Calibri";
const AZUL = "1F3864";

function inline(texto, extra = {}) {
  const runs = [];
  for (const parte of texto.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/)) {
    if (!parte) continue;
    if (parte.startsWith("**")) runs.push(new TextRun({ text: parte.slice(2, -2), bold: true, ...extra }));
    else if (parte.startsWith("`")) runs.push(new TextRun({ text: parte.slice(1, -1), font: "Consolas", size: 20, ...extra }));
    else if (parte.startsWith("*") && parte.length > 2) runs.push(new TextRun({ text: parte.slice(1, -1), italics: true, ...extra }));
    else runs.push(new TextRun({ text: parte, ...extra }));
  }
  return runs;
}

function tamanoPng(ruta) {
  const b = fs.readFileSync(ruta);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), datos: b };
}

const borde = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const bordes = { top: borde, bottom: borde, left: borde, right: borde };

function tabla(filas) {
  const celdas = filas.map((f) => f.replace(/^\||\|$/g, "").split("|").map((c) => c.trim()));
  const cab = celdas[0];
  const cuerpo = celdas.slice(2);
  const n = cab.length;
  // Anchos proporcionales al texto más largo de cada columna (con mínimo y máximo).
  const largo = cab.map((_, j) => Math.min(45, Math.max(8, ...celdas.filter((_, i) => i !== 1).map((r) => (r[j] || "").length))));
  const total = largo.reduce((a, b) => a + b, 0);
  const anchos = largo.map((l) => Math.floor((ANCHO * l) / total));
  anchos[n - 1] += ANCHO - anchos.reduce((a, b) => a + b, 0);
  const fila = (r, esCab) => new TableRow({
    tableHeader: esCab,
    children: r.map((c, j) => new TableCell({
      width: { size: anchos[j], type: WidthType.DXA },
      borders: bordes,
      shading: esCab ? { type: ShadingType.CLEAR, color: "auto", fill: "DCE3EE" } : undefined,
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [new Paragraph({
        spacing: { before: 0, after: 0, line: 252 },
        alignment: j === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
        children: inline(c, { size: 18, bold: esCab ? true : undefined }),
      })],
    })),
  });
  return new Table({
    width: { size: ANCHO, type: WidthType.DXA },
    columnWidths: anchos,
    rows: [fila(cab, true), ...cuerpo.map((r) => fila(r, false))],
  });
}

const portada = [];
const cuerpo = [];
let destino = portada;
let figura = 0;
let tituloHecho = false;

for (let i = 0; i < lineas.length; i++) {
  const l = lineas[i];
  if (!l.trim()) continue;

  if (l.trim() === "---") continue;
  if (l.startsWith(">")) {
    // Cita: bloque sombreado; verde si es un bloque de teoría, azul si es texto para leer en voz alta.
    const bloque = [];
    while (i < lineas.length && lineas[i].startsWith(">")) bloque.push(lineas[i++].replace(/^> ?/, ""));
    i--;
    const teoria = (bloque.find((x) => x.trim()) || "").startsWith("**Teoría");
    const fondo = { type: ShadingType.CLEAR, color: "auto", fill: teoria ? "E7F0E3" : "EDF1F8" };
    for (const b of bloque) {
      if (!b.trim()) continue;
      const v = b.match(/^(\s*)- (.*)$/);
      const n = b.match(/^(\d+)\. (.*)$/);
      const sangria = v ? 567 + 340 * Math.floor(v[1].length / 2) : n ? 567 : 284;
      const hijos = v ? [new TextRun("•  "), ...inline(v[2])] : n ? [new TextRun(`${n[1]}. `), ...inline(n[2])] : inline(b);
      destino.push(new Paragraph({ shading: fondo, indent: { left: sangria, right: 284, hanging: v || n ? 227 : 0 },
        spacing: { before: 0, after: 60 }, children: hijos }));
    }
    destino.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
    continue;
  }
  if (l.startsWith("# ") && !tituloHecho) {
    tituloHecho = true;
    portada.push(new Paragraph({ spacing: { before: 2400, after: 600 }, alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: l.slice(2), bold: true, size: 40, color: AZUL })] }));
    continue;
  }
  if (destino === portada && l.startsWith("**")) {
    portada.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: inline(l, { size: 26 }) }));
    continue;
  }
  if (l.startsWith("## ")) {
    const titulo = l.slice(3);
    if (destino === portada) {
      // Fin de la portada: salto de página, resumen y, después, el índice.
      destino = cuerpo;
    } else if (titulo === "1. Introducción") {
      cuerpo.push(new Paragraph({ children: [new PageBreak()] }));
      // Título con formato de encabezado pero sin nivel de esquema, para que no aparezca en el propio índice.
      cuerpo.push(new Paragraph({ spacing: { before: 360, after: 160 },
        children: [new TextRun({ text: "Contenido", bold: true, size: 30, color: AZUL })] }));
      cuerpo.push(new TableOfContents("Contenido", { hyperlink: true, headingStyleRange: "1-2" }));
      cuerpo.push(new Paragraph({ children: [new PageBreak()] }));
    }
    cuerpo.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(titulo)] }));
    continue;
  }
  if (l.startsWith("### ")) {
    cuerpo.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(l.slice(4))] }));
    continue;
  }
  const img = l.match(/^!\[(.*)\]\((.*)\)$/);
  if (img) {
    figura += 1;
    const { w, h, datos } = tamanoPng(path.resolve(base, img[2]));
    const anchoPx = Math.min(600, w);
    const altoPx = Math.round((anchoPx * h) / w);
    cuerpo.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200, after: 60 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: datos, transformation: { width: anchoPx, height: altoPx } })] }));
    cuerpo.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
      children: [new TextRun({ text: `Figura ${figura}. `, bold: true, size: 19 }), ...inline(img[1], { size: 19, italics: true })] }));
    continue;
  }
  if (l.startsWith("|")) {
    const filas = [];
    while (i < lineas.length && lineas[i].startsWith("|")) filas.push(lineas[i++]);
    i--;
    cuerpo.push(tabla(filas));
    cuerpo.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
    continue;
  }
  const vin = l.match(/^(\s*)- (.*)$/);
  if (vin) {
    const nivel = Math.min(1, Math.floor(vin[1].length / 2));
    const esRef = cuerpo.length && destino === cuerpo && lineas.slice(0, i).reverse().find((x) => x.startsWith("## ")) === "## Referencias";
    if (esRef) {
      cuerpo.push(new Paragraph({ indent: { left: 567, hanging: 567 }, spacing: { after: 100 }, children: inline(vin[2], { size: 21 }) }));
    } else {
      cuerpo.push(new Paragraph({ numbering: { reference: "vinetas", level: nivel }, spacing: { after: 80 }, children: inline(vin[2]) }));
    }
    continue;
  }
  const num = l.match(/^(\s*)(\d+)\. (.*)$/);
  if (num) {
    cuerpo.push(new Paragraph({ indent: { left: 567, hanging: 340 }, spacing: { after: 80 },
      children: [new TextRun(`${num[2]}. `), ...inline(num[3])] }));
    continue;
  }
  const siguiente = lineas.slice(i + 1).find((x) => x.trim());
  destino.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 160 },
    keepNext: Boolean(siguiente && siguiente.startsWith("|")), children: inline(l) }));
}

portada.push(new Paragraph({ children: [new PageBreak()] }));

const doc = new Document({
  creator: "Gabriel Aldana, Harold Fúneme, Laura Rodríguez, Juan Roa",
  title: "Informe final — Portafolio Colombiano",
  styles: {
    default: { document: { run: { font: FUENTE, size: 22 }, paragraph: { spacing: { line: 276 } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FUENTE, size: 30, bold: true, color: AZUL },
        paragraph: { spacing: { before: 360, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FUENTE, size: 25, bold: true, color: "2E5597" },
        paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [{
      reference: "vinetas",
      levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 567, hanging: 283 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1134, hanging: 283 } } } },
      ],
    }],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1418, bottom: 1418, left: 1418, right: 1418 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 18 })] })] }) },
    children: [...portada, ...cuerpo],
  }],
});

Packer.toBuffer(doc).then((b) => { fs.writeFileSync(salida, b); console.log(`ok: ${salida} (${figura} figuras)`); });

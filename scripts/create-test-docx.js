// Minimal DOCX file (valid Office Open XML ZIP structure)
const JSZip = require('jszip');

async function createTestDocx() {
  const zip = new JSZip();

  // [Content_Types].xml
  zip.file('[Content_Types].xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>`);

  // _rels/.rels
  zip.folder('_rels').file('.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>`);

  // word/document.xml
  zip.folder('word').file('document.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr>
        <w:pStyle w:val="Heading1"/>
      </w:pPr>
      <w:r>
        <w:t>Sample Proposal Document</w:t>
      </w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:t>This is a test document for proposal generation.</w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>`);

  // word/_rels/document.xml.rels
  zip.folder('word/_rels').file('document.xml.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>`);

  const buffer = await zip.generateAsync({ type: 'nodebuffer' });
  const fs = require('fs');
  const path = require('path');
  const outputPath = path.join(__dirname, '../tests/fixtures/commands/input-valid/sample.docx');
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, buffer);
  console.log(`Created test DOCX: ${outputPath}`);
}

createTestDocx().catch(console.error);

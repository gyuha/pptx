// Minimal PPTX template file
const JSZip = require('jszip');

async function createTestPptx() {
  const zip = new JSZip();

  // [Content_Types].xml
  zip.file('[Content_Types].xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>`);

  // _rels/.rels
  zip.folder('_rels').file('.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>`);

  // ppt/presentation.xml
  zip.folder('ppt').file('presentation.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:slideIdLst>
    <p:slideId id="256" r:id="rId1" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>
  </p:slideIdLst>
</p:presentation>`);

  // ppt/_rels/presentation.xml.rels
  zip.folder('ppt/_rels').file('presentation.xml.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="../slides/slide1.xml"/>
</Relationships>`);

  // ppt/slides/slide1.xml
  zip.folder('ppt/slides').file('slide1.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:slide xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:spTree>
    <p:nvGrpSpPr/>
    <p:grpSpPr/>
  </p:spTree>
</p:slide>`);

  // ppt/slideLayouts/slideLayout1.xml
  zip.folder('ppt/slideLayouts').file('slideLayout1.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:slideLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:spTree>
    <p:nvGrpSpPr/>
    <p:grpSpPr/>
  </p:spTree>
</p:slideLayout>`);

  const buffer = await zip.generateAsync({ type: 'nodebuffer' });
  const fs = require('fs');
  const path = require('path');
  const outputPath = path.join(__dirname, '../tests/fixtures/commands/template.pptx');
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, buffer);
  console.log(`Created test PPTX template: ${outputPath}`);
}

createTestPptx().catch(console.error);

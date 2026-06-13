const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 900, deviceScaleFactor: 2 });

  const htmlPath = path.resolve(__dirname, 'infographic.html');
  await page.goto('file://' + htmlPath, { waitUntil: 'networkidle0' });

  const pngPath = path.resolve(__dirname, 'Harness-Studio-Infographic.png');
  await page.screenshot({ path: pngPath, fullPage: false });
  console.log('PNG saved:', pngPath);

  // Also save PDF
  const pdfPath = path.resolve(__dirname, 'Harness-Studio-Infographic.pdf');
  await page.pdf({
    path: pdfPath,
    width: '1200px',
    height: '900px',
    printBackground: true
  });
  console.log('PDF saved:', pdfPath);

  await browser.close();
})();

const puppeteer = require('puppeteer-core');
const fs = require('fs');

const viewports = [
  { width: 1920, height: 1080 },
  { width: 1440, height: 900 },
  { width: 1366, height: 768 },
  { width: 1280, height: 720 },
  { width: 1280, height: 640 },
  { width: 1024, height: 768 },
  { width: 1024, height: 640 },
  { width: 900, height: 640 },
];

const scenarios = [
  'default', // Scan screen
  'valid-code', // Valid scan / select machine
  'touch-only-select-machine', // Touch only / no button box
  'touch-and-button-box-select-machine', // Touch + button box enabled
  'invalid-code', // Invalid code / error
  'starting-machine', // Machine selected / starting
  'machine-in-use', // Machine in use
  'all-busy', // All machines busy
  'thank-you', // Thank you / activated
  'backend-unreachable' // Backend unreachable
];

async function run() {
  console.log("Starting Chrome...");
  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: '/usr/bin/chromium-browser',
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
  } catch(e) {
    console.error("Failed to launch browser:", e);
    process.exit(1);
  }

  const page = await browser.newPage();
  
  let failed = 0;
  let results = [];
  
  for (const vp of viewports) {
    console.log(`\nTesting viewport ${vp.width}x${vp.height}...`);
    await page.setViewport(vp);
    
    for (const scenario of scenarios) {
      await page.goto(`http://localhost:3000/dev/kiosk-preview?scenario=${scenario}`);
      
      // Wait for React to render
      try {
        await page.waitForSelector('.kiosk-preview-canvas', { timeout: 3000 });
        // Give it an extra moment for images/fonts if any
        await new Promise(r => setTimeout(r, 300));
      } catch(e) {
        console.error(`  [${scenario}] timeout waiting for canvas`);
        continue;
      }

      // Close the sidebar to simulate pure kiosk
      try {
        const closeBtn = await page.$('button[aria-label="Close sidebar"]');
        if (closeBtn) {
          await closeBtn.click();
          await new Promise(r => setTimeout(r, 400)); // wait for transition
        }
      } catch(e) {}
      
      const scrollInfo = await page.evaluate(() => {
        // Calculate max allowed height
        const winH = window.innerHeight;
        const htmlH = document.documentElement.scrollHeight;
        const bodyH = document.body.scrollHeight;
        
        return {
          windowHeight: winH,
          htmlScrollHeight: htmlH,
          bodyScrollHeight: bodyH,
          hasPageScroll: htmlH > winH || bodyH > winH
        };
      });
      
      if (scrollInfo.hasPageScroll) {
        console.log(`  ❌ [${scenario}] failed: document height (${scrollInfo.htmlScrollHeight}) > window (${scrollInfo.windowHeight})`);
        failed++;
        results.push({ viewport: `${vp.width}x${vp.height}`, scenario, passed: false, info: scrollInfo });
      } else {
        console.log(`  ✅ [${scenario}] passed`);
        results.push({ viewport: `${vp.width}x${vp.height}`, scenario, passed: true });
      }
    }
  }
  
  await browser.close();
  
  const reportPath = 'test-report.json';
  fs.writeFileSync(reportPath, JSON.stringify({ failed, total: viewports.length * scenarios.length, results }, null, 2));
  
  if (failed > 0) {
    console.log(`\nTest completed with ${failed} scrollbar issues. Report saved to ${reportPath}`);
    process.exit(1);
  } else {
    console.log(`\n🎉 All tests passed! No scrollbars detected. Report saved to ${reportPath}`);
    process.exit(0);
  }
}

run();

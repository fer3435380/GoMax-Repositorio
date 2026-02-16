const { defineConfig } = require("cypress");
const fs = require('fs');
const path = require('path');

module.exports = defineConfig({
  e2e: {
    screenshotOnRunFailure: true,
    setupNodeEvents(on, config) {
      on('task',{
        updateModuleList(){
          const modulesPath = path.join(__dirname, '..', 'dependencias');
          const listFile = path.join(__dirname, '..', 'module_list.txt');

          const folders = fs.readdirSync(modulesPath)
          .filter(file => fs.statSync(path.join(modulesPath, file)).isDirectory());

          fs.writeFileSync(listFile, folders.join('\n'));
          console.log('Module list updated:', folders);
          return null;
        }
      })
    },
  },
});

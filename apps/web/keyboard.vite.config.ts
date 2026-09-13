import {defineConfig} from 'vite';
import {fileURLToPath} from 'node:url';
export default defineConfig({root:fileURLToPath(new URL('.',import.meta.url)),publicDir:false,build:{outDir:fileURLToPath(new URL('../../artifacts/keyboard-web',import.meta.url)),emptyOutDir:true,rollupOptions:{input:fileURLToPath(new URL('./keyboard.html',import.meta.url))}}});

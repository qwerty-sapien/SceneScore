import {defineConfig} from 'vite';
import {fileURLToPath} from 'node:url';
export default defineConfig({root:fileURLToPath(new URL('.',import.meta.url)),publicDir:false,build:{outDir:fileURLToPath(new URL('../../artifacts/scenescore-web',import.meta.url)),emptyOutDir:true,rollupOptions:{input:fileURLToPath(new URL('./scenescore.html',import.meta.url))}}});

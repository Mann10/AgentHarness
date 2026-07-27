import * as esbuild from 'esbuild';

await esbuild.build({
  entryPoints: ['src/index.tsx'],
  bundle: true,
  platform: 'node',
  target: 'node18',
  outfile: 'dist/index.js',
  format: 'esm',
  sourcemap: true,
  loader: { '.ts': 'tsx' },
  jsx: 'automatic',
  jsxImportSource: 'react',
  external: ['ink', 'react'],
});

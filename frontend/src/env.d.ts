/// <reference types="vite/client" />

declare module "*.vue";

declare module "plotly.js-cartesian-dist-min" {
  const Plotly: {
    react: (...args: unknown[]) => unknown;
    purge: (...args: unknown[]) => unknown;
  };
  export default Plotly;
}

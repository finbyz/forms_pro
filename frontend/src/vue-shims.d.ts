declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

export {};

declare global {
  interface Window {
    site_name?: string;
    csrf_token?: string;
  }
}

declare module "frappe-ui-text-editor" {
  import type { Component } from "vue";
  const TextEditor: Component;
  export default TextEditor;
}

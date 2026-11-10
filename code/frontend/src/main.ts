import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import "./styles/main.css";
import "./styles/learning-theme.css";

createApp(App).use(createPinia()).mount("#app");


import { AppFrame } from "./AppFrame";
import React from "react";
import ReactDOM from "react-dom/client";
import { Provider } from "react-redux";
import { store } from "./store/store";
import { DashboardPage } from "./pages/DashboardPage";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Provider store={store}>
      <AppFrame><DashboardPage /></AppFrame>
    </Provider>
  </React.StrictMode>
);

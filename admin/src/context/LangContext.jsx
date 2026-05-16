import { createContext, useContext, useState } from "react";
import translations from "../i18n";

const LangContext = createContext();

export function LangProvider({ children }) {
  const [lang, setLang] = useState(
    sessionStorage.getItem("admin_lang") || "es"
  );

  const changeLang = (newLang) => {
    setLang(newLang);
    sessionStorage.setItem("admin_lang", newLang);
  };

  const t = (key) => {
    return translations[lang]?.[key] || translations["es"]?.[key] || key;
  };

  return (
    <LangContext.Provider value={{ lang, changeLang, t }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang() {
  return useContext(LangContext);
}
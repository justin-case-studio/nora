import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import ReactDOM from 'react-dom/client'
import './frontend/styles/index.css'
import 'react-datepicker/dist/react-datepicker.css'

const container = document.getElementById('root')
const root = createRoot(container)

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
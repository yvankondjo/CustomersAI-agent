# Site Web de Test - AI Support Widget

Site web de démonstration pour tester l'intégration du widget de chat AI Support.

## Structure

- `index.html` - Page d'accueil
- `products.html` - Page produits
- `about.html` - Page à propos
- `contact.html` - Page contact
- `styles.css` - Styles CSS communs
- `widget.js` - Widget de chat AI Support

## Utilisation

### Méthode 1 : Ouvrir directement dans le navigateur

1. Assurez-vous que le backend est démarré sur `http://localhost:8000`
2. Ouvrez `index.html` dans votre navigateur
3. Le widget de chat apparaîtra en bas à droite

### Méthode 2 : Utiliser un serveur HTTP local

Pour éviter les problèmes CORS, utilisez un serveur HTTP :

```bash
# Avec Python 3
cd test-site
python -m http.server 3000

# Puis ouvrez http://localhost:3000 dans votre navigateur
```

```bash
# Avec Node.js (si vous avez http-server installé)
cd test-site
npx http-server -p 3000

# Puis ouvrez http://localhost:3000 dans votre navigateur
```

## Configuration du Widget

Le widget est configuré dans chaque page HTML. Vous pouvez modifier les paramètres :

```javascript
AISupportWidget.init({
  baseUrl: 'http://localhost:8000',  // URL du backend
  primaryColor: '#0ea5e9',            // Couleur principale
  title: 'Support AI',                // Titre du chat
  subtitle: 'Comment puis-je vous aider ?',  // Sous-titre
  position: 'bottom-right',           // Position (bottom-right ou bottom-left)
  showBranding: true                  // Afficher le branding
});
```

## Notes

- Le widget nécessite que le backend soit démarré et accessible
- L'endpoint utilisé est `/api/v1/playground/message`
- Le widget fonctionne sur toutes les pages du site


<div align="center">

<img src="https://raw.githubusercontent.com/Abdeltoto/patchwork/main/docs/images/banner.png" alt="Patchwork : laissez votre agent IA modifier FileMaker" width="100%">

<br>

[![CI](https://img.shields.io/github/actions/workflow/status/Abdeltoto/patchwork/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/Abdeltoto/patchwork/actions/workflows/ci.yml)
[![Stars](https://img.shields.io/github/stars/Abdeltoto/patchwork?style=flat-square&color=8b5cf6)](https://github.com/Abdeltoto/patchwork/stargazers)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-14b8a6?style=flat-square)](https://github.com/Abdeltoto/patchwork/blob/main/LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FileMaker 2026](https://img.shields.io/badge/FileMaker-2026-000000?style=flat-square&logo=claris&logoColor=white)
![Serveur MCP](https://img.shields.io/badge/MCP-serveur-000000?style=flat-square&logo=modelcontextprotocol&logoColor=white)
![Zéro dépendance](https://img.shields.io/badge/d%C3%A9pendances-0-f59e0b?style=flat-square)
[![PRs bienvenues](https://img.shields.io/badge/PRs-bienvenues-ff69b4?style=flat-square)](https://github.com/Abdeltoto/patchwork/blob/main/CONTRIBUTING.md)

<a href="#brancher-votre-agent"><img src="https://img.shields.io/badge/Claude_Code-191919?style=for-the-badge&logo=claude&logoColor=D97757" alt="Claude Code"></a>
<a href="#brancher-votre-agent"><img src="https://img.shields.io/badge/Cursor-000000?style=for-the-badge&logo=cursor&logoColor=white" alt="Cursor"></a>
<a href="#brancher-votre-agent"><img src="https://img.shields.io/badge/Codex-000000?style=for-the-badge&logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHJlY3QgeD0iMS41IiB5PSIzIiB3aWR0aD0iMjEiIGhlaWdodD0iMTgiIHJ4PSI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNmZmYiIHN0cm9rZS13aWR0aD0iMiIvPjxwYXRoIGQ9Ik02LjUgOWwzLjUgMy0zLjUgMyIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjxwYXRoIGQ9Ik0xMi41IDE1LjVoNSIgc3Ryb2tlPSIjZmZmIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPjwvc3ZnPg==" alt="Codex"></a>
<a href="#brancher-votre-agent"><img src="https://img.shields.io/badge/Antigravity-1a1a2e?style=for-the-badge&logo=google&logoColor=4285F4" alt="Google Antigravity"></a>

**[Démarrage](#démarrage)** · **[Exemples](#en-action)** · **[Brancher votre agent](#brancher-votre-agent)** · **[Ce qu'il peut modifier](#ce-quil-peut-modifier)** · **[Guide de terrain](https://github.com/Abdeltoto/patchwork/blob/main/docs/fmupgradetool-field-guide.md)** · **[English](https://github.com/Abdeltoto/patchwork/blob/main/README.md)**

</div>

<br>

> **Vendredi, 16 h. Un client demande « juste un petit champ de plus » sur le modèle de détail.**
> Vous connaissez la suite : définir la rubrique, copier l'étiquette, décaler chaque objet en dessous, agrandir la partie… puis tout recommencer sur le modèle suivant.
>
> **Patchwork confie ces clics à votre agent IA.** Demandez simplement, avec vos mots, comme vous le demanderiez à un collègue. Votre agent ajoute la rubrique et la place exactement où vous l'avez dit, écrit des scripts, crée des listes de valeurs et refait le style des modèles, dans un vrai fichier `.fmp12`. Chaque modification est vérifiée, chaque modification peut être annulée, et votre fichier d'origine n'est jamais touché.

Gratuit et open source. Fonctionne avec Claude Code, Cursor, Codex et Antigravity.

<p align="center"><a href="https://youtu.be/g5UkJLiYAhA"><img src="https://raw.githubusercontent.com/Abdeltoto/patchwork/main/docs/images/video-card.fr.jpg" alt="Regarder la présentation de Patchwork en 90 secondes sur YouTube" width="80%"></a><br><sub>▶ <a href="https://youtu.be/g5UkJLiYAhA">Regarder la présentation en 90 secondes sur YouTube</a> · <a href="https://youtu.be/AkFhBpB0YYY">English version</a></sub></p>

## Démarrage

Trois commandes, et ensuite vous parlez simplement à votre agent.

```bash
pip install fm-patchwork
patchwork doctor          # trouve les outils en ligne de commande Claris
patchwork init .          # branche ce dossier pour Claude Code, Cursor, Codex et Antigravity
```

Sans installation, avec [uv](https://docs.astral.sh/uv/) : `uvx fm-patchwork doctor`, et `uvx fm-patchwork mcp` comme commande du serveur MCP.

Puis demandez à votre agent : *« Ouvre Invoice.fmp12 et ajoute une rubrique Status dans Clients. »* C'est tout.

### Bon à savoir

- **Il modifie la structure, pas les enregistrements.** Rubriques, scripts, modèles, listes de valeurs, thèmes. Pour vos données, utilisez la Data API ou OData.
- **Il travaille sur des fichiers fermés, pas sur des fichiers hébergés.** Modifiez une copie, testez-la, puis déployez-la comme d'habitude.
- **Il a besoin des outils en ligne de commande Claris** (FMUpgradeTool et FMDeveloperTool). Ils sont fournis avec l'installeur de FileMaker Server, la version d'essai gratuite suffit et aucun serveur n'a besoin de tourner : [installer les outils Claris](https://github.com/Abdeltoto/patchwork/blob/main/docs/install-fmupgradetool.md). Patchwork lui-même n'a aucune autre dépendance.

## En action

Quatre vraies sessions sur la solution gratuite [Claris Invoice](https://marketplace.claris.com/detail/2000.html). Pour chacune : la demande, ce que l'agent a fait, et le fichier avant et après. Aucune maquette.

<p align="center"><img src="https://raw.githubusercontent.com/Abdeltoto/patchwork/main/docs/images/example-schema.png" alt="Prompt : ajouter une rubrique Loyalty Tier et une liste de valeurs. La rubrique et la liste apparaissent dans le fichier." width="100%"></p>

<p align="center"><img src="https://raw.githubusercontent.com/Abdeltoto/patchwork/main/docs/images/example-script.png" alt="Prompt : écrire un script Say Hello. L'agent copie un vrai pas de dialogue et crée un script de deux pas." width="100%"></p>

<p align="center"><img src="https://raw.githubusercontent.com/Abdeltoto/patchwork/main/docs/images/example-cleanup.png" alt="Prompt : supprimer les modèles Dev. Six modèles sont supprimés et l'agent signale trois scripts qui les utilisaient." width="100%"></p>

<p align="center"><img src="https://raw.githubusercontent.com/Abdeltoto/patchwork/main/docs/images/example-rebrand.png" alt="Prompt : rebrander pour Maple and Oak. L'en-tête bleu Claris devient un en-tête vert forêt Maple and Oak." width="100%"></p>

## Comment ça marche

<p align="center"><img src="https://raw.githubusercontent.com/Abdeltoto/patchwork/main/docs/images/how-it-works.jpg" alt="Un agent IA coud des pièces sur un fichier FileMaker, avec une coche de vérification et une flèche d'annulation" width="80%"></p>

Pourquoi votre agent ne peut-il pas le faire seul ? Un fichier FileMaker est un fichier binaire, et sa structure se cache derrière des fenêtres qu'un agent ne peut pas cliquer. Claris fournit bien une porte d'entrée en ligne de commande, [FMUpgradeTool](https://help.claris.com/en/app-upgrade-tool-guide/content/index.html), mais elle est exigeante : chaque objet est désigné par un UUID, et un patch légèrement faux est **ignoré en silence**, alors que l'outil affiche quand même `Patch File Applied`.

Patchwork est l'assistant minutieux entre les deux :

| | |
|:-:|---|
| 🧵 **Écrit le patch** | Lit l'export XML du fichier et construit un patch avec les bons UUID, identifiants et catalogues, pour que votre agent n'ait pas à le faire |
| 🔍 **Vérifie le résultat** | Réexporte le fichier après chaque modification et le compare à la version précédente. Si FileMaker a ignoré quelque chose, la modification est refusée au lieu d'être perdue en silence |
| 🧭 **Prévient avant de casser** | Avant une suppression, liste les scripts, modèles et calculs qui utilisent l'objet, et attend votre feu vert |
| 🕐 **Garde chaque version** | Chaque modification est une version numérotée avec son diff. Vous changez d'avis ? `undo` fonctionne toujours |
| 🔒 **Protège l'original** | Tout se passe sur une copie de travail. `save` écrit un nouveau fichier et n'écrase jamais le vôtre |

Plus de détails dans [comment ça marche](https://github.com/Abdeltoto/patchwork/blob/main/docs/how-it-works.md).

## Brancher votre agent

Une seule commande prépare tout. Lancez `patchwork init .` dans le dossier de votre projet, nouveau ou existant : elle ajoute les règles, les skills et la configuration MCP de chaque agent, et conserve les fichiers déjà présents.

| Agent | Configuration écrite par `init` | Ensuite |
|---|---|---|
| <img src="https://cdn.simpleicons.org/claude/D97757" width="16"> **Claude Code** | `.mcp.json` · `CLAUDE.md` · `.claude/skills/` | Lancez `claude` dans le dossier et acceptez `patchwork` |
| <img src="https://cdn.simpleicons.org/cursor/808080" width="16"> **Cursor** | `.cursor/mcp.json` · `.cursor/skills/` | Activez `patchwork` dans Settings › MCP |
| ⌨️ **Codex** | `.codex/config.toml` · `AGENTS.md` · `.agents/skills/` | Faites confiance au projet quand Codex le demande |
| <img src="https://cdn.simpleicons.org/google/4285F4" width="16"> **Antigravity** | `.agents/mcp_config.json` · `AGENTS.md` · `.agents/skills/` | Ouvrez le dossier comme espace de travail |

Chaque agent reçoit les mêmes 21 outils via `patchwork mcp`, un serveur MCP stdio. Le mot de passe de votre fichier reste à vous : définissez-le une fois dans votre terminal avec `PATCHWORK_PASSWORD`, et les agents ne le voient jamais. Configuration manuelle et liste des outils : [agents IA](https://github.com/Abdeltoto/patchwork/blob/main/docs/ai-agents.md).

## Ce qu'il peut modifier

Des rubriques, des scripts en texte brut, des listes de valeurs, les couleurs et les polices, et même une refonte graphique complète. Chaque opération ci-dessous a été essayée sur de vrais fichiers et confirmée par un nouvel export.

| | Ajouter | Modifier | Supprimer |
|---|:-:|:-:|:-:|
| **Rubriques** · texte, nombre, date, heure, horodatage, conteneur, calcul, globale | ✅ | | ✅ |
| **Scripts**, lus et écrits en texte FileMaker | ✅ | ✅ | ✅ |
| **Listes de valeurs** | ✅ | ✅ | ✅ |
| **Fonctions personnalisées** | ✅ | ✅ | ✅ |
| **Modèles** · placer une rubrique avec son étiquette, modèle entier, couleurs, polices, remplacer une rubrique | ✅ rubrique | ✅ | ✅ |
| **Thèmes** · couleurs, polices, nom | | ✅ | |
| **Tables**, occurrences de table | 👁 lecture | | |

> [!TIP]
> Les scripts se lisent et s'écrivent comme dans l'espace de travail des scripts, un pas par ligne :
> `Set Field [ Clients::Status ; "Gold" ]`. Modifiez le texte de `patchwork show script NOM` et renvoyez-le avec `set-steps` : les lignes inchangées gardent leur pas exact, et chaque pas est relu après la modification, donc un paramètre perdu est détecté.

Ce que FMUpgradeTool ne sait pas faire (les données des enregistrements, un thème entièrement nouveau, un objet de modèle seul) est listé dans [le guide de terrain](https://github.com/Abdeltoto/patchwork/blob/main/docs/fmupgradetool-field-guide.md).

## Sans agent

Vous préférez le terminal ? Tout ce que fait l'agent est une commande ordinaire, que vous pouvez lancer vous-même :

```bash
patchwork open "Invoice.fmp12" --account Admin     # copie de travail, version v000
patchwork add-field Clients "Loyalty Tier"
patchwork add-value-list "Loyalty Tiers" Bronze Silver Gold
patchwork log                                       # chaque version et ce qui a changé
patchwork undo
patchwork save "Invoice v2.fmp12"
```

<details>
<summary><b>Toutes les commandes</b></summary>

<br>

| Commande | Rôle |
|---|---|
| `open SRC --account NOM` | Crée une copie de travail dans `.patchwork/` (version v000). La source n'est jamais modifiée |
| `status`, `log` | Version courante, et chaque version avec ce qui a changé |
| `ls [TYPE] [TABLE]` | Liste les modèles, scripts, listes de valeurs, fonctions, thèmes, tables, rubriques |
| `show TYPE NOM` | Affiche un script en texte FileMaker (`--xml` pour le XML), le reste en XML. `show step NOM` affiche un vrai exemple de pas |
| `add-field TABLE NOM` | Ajoute une rubrique : `--type`, `--calc`, `--global`, `--image logo.png` |
| `add-value-list NOM VALEURS...` | Ajoute une liste de valeurs personnalisée |
| `add-custom-function NOM --calc` | Ajoute une fonction personnalisée, avec `--param` |
| `add-script NOM PAS.txt` | Crée un script à partir de texte FileMaker (ou de XML `<Step>`) |
| `set-steps`, `append-steps` | Réécrit un script avec le texte de `show` modifié, ou ajoute des pas à la fin |
| `place-field MODÈLE TO::RUBRIQUE --near RUBRIQUE` | Place une rubrique sous une autre, avec une copie de son apparence et de son étiquette. `--side right`, `--label` |
| `replace TYPE NOM FICHIER.xml` | Remplace un objet par votre version modifiée de `show` |
| `uses TYPE NOM` | Liste ce qui référence un objet, et où son nom apparaît dans les calculs |
| `delete TYPE NOM` | Supprime un script, un modèle, une liste, une fonction ou une rubrique. Refusé tant que d'autres objets l'utilisent, sauf avec `--force` |
| `retheme`, `recolor-layouts` | Réécrit couleurs et polices d'un thème, ou des styles locaux des modèles |
| `push PATCH.xml` | Applique un patch FMUpgradeTool écrit à la main, avec les mêmes vérifications |
| `undo` | Retire la dernière version |
| `save DEST` | Écrit la version courante dans un nouveau `.fmp12` |
| `rebrand SRC DEST --brand brand.json` | En une fois : couleurs, polices, logo et nom du thème sur toute une solution |
| `mcp` | Le serveur MCP pour les agents |
| `init DOSSIER` | Branche un dossier pour Claude Code, Cursor, Codex et Antigravity |
| `doctor` | Montre quels outils Claris Patchwork a trouvés |

Chaque commande de modification accepte `-m "note"` pour le journal et `--dry-run` pour écrire le patch sans l'appliquer. Plus d'exemples dans [exemples et recettes](https://github.com/Abdeltoto/patchwork/tree/main/examples).

</details>

## Le guide de terrain FMUpgradeTool

Le [guide de terrain](https://github.com/Abdeltoto/patchwork/blob/main/docs/fmupgradetool-field-guide.md) rassemble tous les pièges que FMUpgradeTool tend sans prévenir, découverts à la dure sur de vrais fichiers. Utile même si vous n'utilisez jamais Patchwork. Un aperçu :

- sans `--generateGUIDs`, les patchs de thème et de rubrique sont ignorés ;
- l'UUID d'un modèle n'est **pas** le premier `<UUID>` qu'il contient ;
- remplacer un seul objet de modèle est ignoré, remplacer le modèle entier fonctionne ;
- supprimer un pas de script demande un `ScriptReference` dans chaque `ScriptStepReference`.

Vous en avez trouvé un autre ? [Ajoutez-le](https://github.com/Abdeltoto/patchwork/issues/new?template=field-guide.yml).

## FAQ

<details>
<summary><b>Est-ce que ça marche sur des fichiers hébergés ?</b></summary>
<br>
Patchwork travaille sur des fichiers <code>.fmp12</code> fermés, sur disque. Prenez une copie du fichier hébergé, modifiez-la, testez-la, puis déployez-la comme d'habitude, ou transférez les données avec le Claris Data Migration Tool.
</details>

<details>
<summary><b>L'agent peut-il modifier les enregistrements ?</b></summary>
<br>
Non, FMUpgradeTool ne change que la structure. Pour les enregistrements, utilisez la Data API ou OData. Le skill <code>fm-data</code> explique comment.
</details>

<details>
<summary><b>Quelles versions de FileMaker ?</b></summary>
<br>
Développé et vérifié avec FileMaker 2026 (26.0.3). Les versions antérieures qui fournissent FMUpgradeTool et <code>FMDeveloperTool --saveAsXML</code> devraient fonctionner mais n'ont pas été testées. Un retour, positif ou non, est le bienvenu.
</details>

<details>
<summary><b>macOS et Linux ?</b></summary>
<br>
Partout où les outils Claris tournent. La CI tourne sous Windows, macOS et Linux.
</details>

<details>
<summary><b>Mon mot de passe est-il en sécurité avec un agent ?</b></summary>
<br>
Oui. Il est lu dans la variable d'environnement <code>PATCHWORK_PASSWORD</code>, transmis aux outils Claris et affiché <code>***</code>. Il n'est jamais écrit dans un fichier de configuration ni montré à l'agent.
</details>

## Contribuer

Un nouveau piège FMUpgradeTool, une recette, une opération qui vous manque ? Tout est bienvenu : commencez par [CONTRIBUTING.md](https://github.com/Abdeltoto/patchwork/blob/main/CONTRIBUTING.md). Et si Patchwork vous rend votre vendredi après-midi, une ⭐ aide d'autres développeurs FileMaker à le trouver.

<a href="https://star-history.com/#Abdeltoto/patchwork&Date">
  <img src="https://api.star-history.com/svg?repos=Abdeltoto/patchwork&type=Date" alt="Historique des étoiles" width="600">
</a>

## Licence

[MIT](https://github.com/Abdeltoto/patchwork/blob/main/LICENSE). Patchwork est un projet communautaire, sans lien avec Claris International Inc. ni soutien de sa part. FileMaker et Claris sont des marques de Claris International Inc. Les autres noms de produits et logos appartiennent à leurs propriétaires.

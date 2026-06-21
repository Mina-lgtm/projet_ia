# Points extraits de la grille CISIA

Source : `docs/kit candidat 02_Grille Evaluation_CISIA_V1.0.xlsx`.

## C1

C1. Identifier un jeu de données pour répondre aux besoins métiers et aux cas d’usage, en tenant compte des enjeux de pertinence et de cohérence.

Le jeu de données créé est représentatif et adapté aux besoins métiers et aux cas d’usage :
•	Les besoins métiers sont correctement identifiés.
•	Les cas d’usages sont correctement décrits.
•	Les données a priori pertinentes (et celles nécessaires a minima) pour alimenter le modèle d'IA sont identifiées.
•	L’existence, la disponibilité et l'accès des données sont vérifiés.
•	Le cas échéant, des solutions alternatives sont envisagées en cas d'indisponibilité, d'absence ou d'inaccessibilité des données.

## C2

C2. Identifier les risques éthiques et sociétaux à prendre en compte dans le cadre de l’exploitation de la solution d’IA pour prévenir les dérives éventuelles, en tenant compte du cadre règlementaire.

Les risques éthiques et sociétaux associés à l’exploitation de la solution d'IA sont correctement identifiés et pris en compte : 
•	Les chartes éthiques (européennes et françaises) sont connues et appliquées.
•	Les impacts éthiques et sociétaux liés au déploiement de la solution d’IA sont connus et leurs conséquences comprises.
•	Les biais potentiels ou existants sont identifiés lorsque cela est possible.
•	Les dilemmes éthiques sont identifiés le cas échéant. 
•	Les risque éthiques et sociétaux identifiés sont portés à la connaissance des acteurs concernés (commanditaire, juristes, etc.).
•	La vérification par les acteurs concernés des problèmes légaux et éthiques liés au jeu de données est faite.

## C3

C3. Préparer les données pour renforcer leur intégrité et leur pertinence en vue du développement de la solution IA, en mobilisant les techniques de traitement adaptées et en tenant compte des attendus (besoins métiers, cas d’usage etc.) identifiés en phase de cadrage du projet.

exploitation efficace et cohérente par rapport aux attendus du projet : 
•	Les données sont correctement nommées ou renommées.
•	Le format des données est adapté à l'usage auquel elles sont destinées.
•	Les données altérées, inexactes ou non pertinentes sont corrigées ou supprimées (blancs effacés, suppression des fichiers vides et des doublons, etc.).
•	Les traitements effectués sont correctement documentés.
•	Le choix du modèle de stockage (object storage, base de données de documents, base de données relationnelle, etc.) est adapté aux types de données détenues et aux types d'usages auxquels elles sont destinées.
•	Le cycle de vie du jeu de données est correctement documenté (accessibilité des données résultant du traitement vérifiée, prise en compte de usages futurs, des caractéristiques des cas d’usage, de la gouvernance, etc.).
•	Le cycle de vie du jeu de données dûment documenté est soumis aux parties prenantes.

## C4

C4. Choisir un modèle IA pour disposer d’une solution adaptée et performante par rapport aux cas d‘usage, en mesurant sa pertinence et en mobilisant une démarche scientifique.

Le modèle d'IA choisi offre une solution adaptée et performante par rapport aux cas d’usage :
•	La pertinence du modèle est évaluée grâce aux bons indicateurs (analyse  Receiver Operating Characteristic, ou ROC).
•	Les contraintes opérationnelles sont effectivement prises en compte.
•	Les contraintes en matière d’éco-conception sont portées à la connaissance des acteurs pertinents pour choisir la stratégie adaptée.
•	Les grandes familles d'algorithmes sont connues (outils, contraintes, etc.).
•	La démarche scientifique (critères, problématiques, etc.) est correctement documentée.
•	La performance attendue est déterminée (niveau de précision, temps de traitement et d’inférence, prise en compte des déterminants de la performance énergétique, etc.).
•	Le type de résultat attendu est identifié (probabiliste, déterministe, etc.).
•	Le contexte des cas d’usage est pris en compte.
•	Le modèle d'apprentissage choisi est cohérent par rapport aux résultats attendus.
•	La pertinence d’utiliser des solutions techniques sur l’étagère est évaluée le cas échéant.

## C5

C5. Entrainer le modèle d’IA de façon automatique et supervisée pour valider la pertinence des solutions envisagées, au regard des cas d’usage énoncés par le métier.

La méthode d'entrainement du modèle d’IA est adaptée aux résultats attendus :
•	Le modèle d'apprentissage est optimisé suivant le contexte du projet.
•	Le modèle créé est entrainé le cas échéant.
•	Le modèle choisi est réentraîné le cas échéant. 
•	Les connaissances sont transférées d’un modèle à l’autre le cas échéant.
•	Les hyperparamètres du modèle sont décrits.
•	Le travail de feature engineering est effectué lorsque c’est possible (usages classes plutôt que valeurs brutes, réduction de la taille du data set pour optimiser les performances via l’usage de dérivés, etc.).

## C6

C6. Implémenter le modèle d’IA en intégrant les briques technologiques (moteurs, reporting, suivi des prévisions etc.) au sein de l’environnement technique choisi pour exploiter la solution.

L’exploitation de la solution est permise par l’intégration des briques technologiques au sein de l’environnement technique choisi :
•	Le processus de livraison et de déploiement continu est mis en œuvre.
•	Le versionning est implémenté.
•	Les besoins d’intégration sont documentés.

## C7

C7. Contribuer à la conception et à l’évaluation de la proposition d’architecture cible, en identifiant les contraintes avec l’appui des acteurs pertinents, pour garantir les performances attendues.

La pertinence de l’architecture cible est évaluée avec l’appui des acteurs ressources :
•	Les principales architectures et leurs contraintes sont connues.
•	Les contraintes économiques des différents scénarios sont portées à la connaissance des acteurs pertinents pour dimensionner au mieux la proposition d’architecture.
•	Le cas échéant les acteurs métiers et / ou le commanditaire et / ou les acteurs techniques du projet sont interrogés pour préciser les contraintes techniques liées à la généralisation de la solution.

## C8

C8. Mesurer la performance et les impacts de la solution d’IA  pour maintenir son application fonctionnelle, conformément aux cas d’usage et aux enjeux identifiés.

La performance de la solution d'IA est correctement mesurée : 
•	Des indicateurs de performance (et seuils associés) adaptés aux attendus de la solution IA sont définis. 
•	La performance de la solution est mesurée grâce au suivi des indicateurs définis.
•	Les résultats de l'exploitation de la solution IA sont interprétés et présentés aux interlocuteurs concernés.
•	Les actions adaptées sont le cas échant déclenchées en fonction des résultats de l'analyse des indicateurs.

## C9

C9. Adopter une démarche d’amélioration continue de la solution IA, pour garantir son évolution au fil du temps, dans le respect des exigences de la commande initiale et en tenant compte des évolutions des besoins utilisateurs et des données mobilisables.

La permanence de l'adéquation de la solution d'IA avec les besoins identifiés est assurée grâce à la mise en place d'un cadre d'évaluation pertinent et évolutif : 
•	Un système d’évaluation automatisé du modèle d’IA et totalement intégré aux processus CI/CD grâce aux pratiques MLOPS est mis en place
•	Les métriques (taux de prévision, robustesse, variations de performance, obsolescence, etc.) sont intégrées.
•	La pertinence des indicateurs de performance est interrogée selon une périodicité définie en phase de cadrage du projet.

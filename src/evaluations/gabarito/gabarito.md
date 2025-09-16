# frontend_copy
This is a frontend web application built with Next.js and React. It utilizes Material-UI with Emotion for styling and offers internationalization support for English and Portuguese. The application structure suggests multiple pages like About, Article, Contact, Profile, and includes common components such as Dashboard and News.

# Main technologies of this repository
*   **Framework**: Next.js
*   **UI Library**: React
*   **Styling**: Material-UI (MUI), Emotion
*   **Language**: TypeScript
*   **Internationalization**: Next-Intl
*   **Linting**: ESLint

# Main File Structure
*   `.eslintrc.json`: ESLint configuration for maintaining code quality.
*   `.gitignore`: Specifies intentionally untracked files to be ignored by Git.
*   `next.config.mjs`: Configuration file for Next.js.
*   `package.json`, `package-lock.json`: Define project metadata, scripts, and manage dependencies.
*   `tsconfig.json`: TypeScript compiler configuration.
*   `src/`: Contains the main application source code.
    *   `app/`: Implements the Next.js App Router structure.
        *   `layout.tsx`: Defines the root layout for the application.
        *   `page.tsx`: The root page of the application.
        *   `globals.css`, `page.module.css`: Global and module-specific CSS styles.
        *   `Styledroot.tsx`, `theme.ts`: Custom styling and theming configurations using Emotion and MUI.
        *   `favicon.ico`, `fonts/`: Static assets like favicons and custom fonts.
        *   `about/`, `article/`, `contact/`, `profile/`, `result/`: Directories for individual application pages/routes.
    *   `components/`: Reusable UI components.
        *   `common/`: Generic components such as `Dashboard.tsx` and `News.tsx`.
        *   `layout/`: Components related to the overall application layout, including `Footer.tsx` and `MainMenu.tsx`.
    *   `locales/`: Stores internationalization files.

# How to run the project
1.  **Install Dependencies**:
    ```bash
    npm install
    # or
    yarn install
    ```
2.  **Run Development Server**:
    ```bash
    npm run dev
    # or
    yarn dev
    ```
    Open [http://localhost:3000](http://localhost:3000) in your browser.
3.  **Build for Production**:
    ```bash
    npm run build
    # or
    yarn build
    ```
4.  **Start Production Server**:
    ```bash
    npm start
    # or
    yarn start
    ```
    This will serve the production build.
5.  **Run Linter**:
    ```bash
    npm run lint
    # or
    yarn lint
    ```

# Language or internalization
The project supports internationalization using `next-intl`. Language files are located in `src/locales/`. Currently, it provides translations for:
*   English (`en.json`)
*   Portuguese (`pt.json`)
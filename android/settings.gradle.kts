pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}
plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "dashboard-app"
include(":app")

// Redirect build output to outside OneDrive so file-lock conflicts don't block the build.
// OneDrive syncs everything inside the project folder, including build intermediates, and
// holds open handles that prevent Gradle from cleaning them between builds.
gradle.allprojects {
    layout.buildDirectory.set(File("C:/builds/dashboard-app/${project.name}"))
}

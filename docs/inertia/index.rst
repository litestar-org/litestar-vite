==========
Inertia.js
==========

Build server-driven single-page applications with Litestar routes, Inertia responses, and the same asset/runtime system used for the rest of the project.

.. seealso::
   Official Inertia.js docs: `Getting Started <https://inertiajs.com/>`_

.. grid:: 1 1 2 2
   :gutter: 2

   .. grid-item-card:: :octicon:`rocket` Installation
      :link: installation
      :link-type: doc

      Turn on the Inertia plugin, add session middleware, and wire the frontend entrypoint correctly.

   .. grid-item-card:: :octicon:`workflow` How It Works
      :link: how-it-works
      :link-type: doc

      Understand the request headers, initial page payload, partial reload protocol, and response lifecycle.

   .. grid-item-card:: :octicon:`gear` Configuration
      :link: configuration
      :link-type: doc

      Control script-element bootstrap, SSR, page props, redirects, history encryption, and Precognition.

   .. grid-item-card:: :octicon:`server` SSR Reference
      :link: ../reference/inertia/ssr
      :link-type: doc

      See how the Node SSR renderer fits into the existing Litestar integration without turning into framework proxy mode.

Starter Paths
-------------

.. grid:: 1 1 2 2
   :gutter: 2

   .. grid-item-card:: :octicon:`browser` Pages and Responses
      :link: pages
      :link-type: doc

      Start with page components, response helpers, redirects, links, and form handling.

   .. grid-item-card:: :octicon:`database` Data and Props
      :link: shared-data
      :link-type: doc

      Move from shared data to partial reloads, deferred props, once props, merging, polling, prefetching, and infinite scroll.

   .. grid-item-card:: :octicon:`shield-check` Security and Validation
      :link: csrf-protection
      :link-type: doc

      Cover CSRF, history encryption, Precognition, validation, and error handling.

   .. grid-item-card:: :octicon:`code` TypeScript Integration
      :link: typescript
      :link-type: doc

      Generate page prop metadata, share types with the frontend, and keep SSR/bootstrap behavior aligned.

.. toctree::
   :maxdepth: 1
   :caption: Getting Started

   installation
   configuration

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts

   how-it-works

.. toctree::
   :maxdepth: 1
   :caption: The Basics

   pages
   responses
   redirects
   routing
   links
   forms
   file-uploads
   validation

.. toctree::
   :maxdepth: 1
   :caption: Data & Props

   shared-data
   flash-data
   partial-reloads
   deferred-props
   once-props
   merging-props
   load-when-visible
   polling
   prefetching
   infinite-scroll
   remembering-state

.. toctree::
   :maxdepth: 1
   :caption: Security

   csrf-protection
   history-encryption
   precognition

.. toctree::
   :maxdepth: 1
   :caption: Advanced

   templates
   error-handling
   asset-versioning

.. toctree::
   :maxdepth: 1
   :caption: TypeScript Integration

   typescript
   type-generation
   typed-page-props
   shared-props-typing

.. toctree::
   :maxdepth: 1
   :caption: Examples

   fullstack-example

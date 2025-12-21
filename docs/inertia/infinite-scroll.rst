===============
Infinite Scroll
===============

Load more items as the user scrolls.

.. seealso::
   Official Inertia.js docs: `Infinite Scroll <https://inertiajs.com/infinite-scroll>`_

What Is Infinite Scroll?
------------------------

Infinite scroll combines partial reloads with merge props so new data is
appended to the existing list rather than replacing it.

Backend Usage
-------------

Mark list props as mergeable and provide scroll metadata:

.. code-block:: python

   from litestar import get
   from litestar_vite.inertia import merge, scroll_props, InertiaResponse

   @get("/posts", component="Posts")
   async def list_posts(page: int = 1) -> InertiaResponse:
       posts = await Post.paginate(page=page, per_page=20)
       return InertiaResponse(
           {"posts": merge("posts", posts.items, match_on="id")},
           scroll_props=scroll_props(
               page_name="page",
               current_page=page,
               previous_page=page - 1 if page > 1 else None,
               next_page=page + 1 if posts.has_next else None,
           ),
       )

Automatic Scroll Props
----------------------

You can also return a pagination container and enable ``infinite_scroll`` on
the route. Litestar-Vite will extract items and scroll props for you:

.. code-block:: python

   from litestar.pagination import OffsetPagination

   @get("/posts", component="Posts", infinite_scroll=True, key="posts")
   async def list_posts(offset: int = 0, limit: int = 20) -> OffsetPagination[Post]:
       posts, total = await Post.paginate(offset=offset, limit=limit)
       return OffsetPagination(items=posts, total=total, limit=limit, offset=offset)

Frontend Usage
--------------

Trigger partial reloads when the bottom sentinel becomes visible:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { usePage, WhenVisible } from "@inertiajs/react";

         export default function Posts() {
           const page = usePage();
           const { posts } = page.props;
           const { scrollProps } = page;

           return (
             <div>
               {posts.map((post) => (
                 <PostCard key={post.id} post={post} />
               ))}

               {scrollProps?.nextPage && (
                 <WhenVisible
                   always
                   params={{ only: ["posts"], data: { page: scrollProps.nextPage } }}
                 >
                   <Spinner />
                 </WhenVisible>
               )}
             </div>
           );
         }

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import { usePage, WhenVisible } from "@inertiajs/vue3";

         const page = usePage();
         const { posts } = page.props;
         </script>

         <template>
           <div>
             <PostCard v-for="post in posts" :key="post.id" :post="post" />

             <WhenVisible
               v-if="page.scrollProps?.nextPage"
               always
               :params="{ only: ['posts'], data: { page: page.scrollProps.nextPage } }"
             >
               <Spinner />
             </WhenVisible>
           </div>
         </template>

Tips
----

- Use ``match_on`` in ``merge()`` to avoid duplicates when refreshing.
- Use ``page_name`` to isolate multiple scroll regions on one page.
- Combine with :doc:`remembering-state` to preserve filters across visits.

See Also
--------

- :doc:`merging-props` - Merge strategies and match_on
- :doc:`load-when-visible` - WhenVisible patterns
- :doc:`partial-reloads` - Partial reload mechanics

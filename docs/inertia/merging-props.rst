=============
Merging Props
=============

Combine new data with existing props for infinite scroll and live updates.

.. seealso::
   Official Inertia.js docs: `Merging Props <https://inertiajs.com/merging-props>`_

The merge() Helper
------------------

Use ``merge()`` to append or prepend data instead of replacing:

.. code-block:: python

   from litestar_vite.inertia import merge

   @get("/posts", component="Posts")
   async def list_posts(page: int = 1) -> dict:
       posts = await Post.paginate(page=page, per_page=20)
       return {
           "posts": merge("posts", posts.items),  # Append to existing
       }

Merge Strategies
----------------

.. code-block:: python

   # Append new items to end (default)
   merge("posts", new_posts)
   merge("posts", new_posts, strategy="append")

   # Prepend new items to beginning
   merge("messages", new_messages, strategy="prepend")

   # Deep merge nested objects
   merge("settings", updated_settings, strategy="deep")

Match On Key
------------

Update existing items instead of duplicating:

.. code-block:: python

   # Match items by ID - updates existing, appends new
   merge("posts", updated_posts, match_on="id")

   # Match on multiple keys
   merge("items", items, match_on=["type", "id"])

Infinite Scroll
---------------

Complete infinite scroll example:

Backend
~~~~~~~

.. code-block:: python

   from litestar_vite.inertia import merge, scroll_props

   @get("/posts", component="Posts")
   async def list_posts(page: int = 1) -> dict:
       posts = await Post.paginate(page=page, per_page=20)
       return {
           "posts": merge("posts", posts.items),
           "pagination": scroll_props(
               page_name="page",
               current_page=page,
               previous_page=page - 1 if page > 1 else None,
               next_page=page + 1 if posts.has_next else None,
           ),
       }

Frontend
~~~~~~~~

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { usePage, router, WhenVisible } from "@inertiajs/react";

         interface Props {
           posts: Post[];
           pagination: {
             nextPageUrl?: string;
           };
         }

         export default function Posts({ posts, pagination }: Props) {
           return (
             <div>
               {posts.map((post) => (
                 <PostCard key={post.id} post={post} />
               ))}

               {pagination.nextPageUrl && (
                 <WhenVisible
                   always
                   params={{ only: ["posts"], data: { page: currentPage + 1 } }}
                 >
                   <Spinner />
                 </WhenVisible>
               )}
             </div>
           );
         }

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup>
         import { router, WhenVisible } from "@inertiajs/vue3";

         const props = defineProps<{
           posts: Post[];
           pagination: { nextPageUrl?: string };
         }>();
         </script>

         <template>
           <div>
             <PostCard v-for="post in posts" :key="post.id" :post="post" />

             <WhenVisible
               v-if="pagination.nextPageUrl"
               always
               :params="{ only: ['posts'], data: { page: currentPage + 1 } }"
             >
               <Spinner />
             </WhenVisible>
           </div>
         </template>

scroll_props() Helper
---------------------

Create pagination metadata for infinite scroll:

.. code-block:: python

   from litestar_vite.inertia import scroll_props

   scroll_props(
       page_name="page",        # Query parameter name
       current_page=1,          # Current page number
       previous_page=None,      # None if at first page
       next_page=2,             # None if at last page
   )

Automatic Pagination
--------------------

Return pagination objects directly - scroll props are extracted:

.. code-block:: python

   from litestar.pagination import OffsetPagination

   @get("/posts", component="Posts", infinite_scroll=True)
   async def list_posts(offset: int = 0, limit: int = 20) -> OffsetPagination:
       posts, total = await Post.paginate(offset, limit)
       return OffsetPagination(items=posts, offset=offset, limit=limit, total=total)

The ``infinite_scroll=True`` opt enables automatic scroll_props extraction.

Protocol Response
-----------------

Merge props are indicated in the response:

.. code-block:: json

   {
     "component": "Posts",
     "props": {"posts": ["Post 1", "Post 2"]},
     "mergeProps": ["posts"],
     "scrollRegion": {
       "pageName": "page",
       "currentPage": 1,
       "nextPageUrl": "/posts?page=2"
     }
   }

See Also
--------

- :doc:`partial-reloads` - Partial reload mechanics
- :doc:`deferred-props` - Deferred loading

=================
Load When Visible
=================

Lazy-load props when elements enter the viewport.

.. seealso::
   Official Inertia.js docs: `Load When Visible <https://inertiajs.com/docs/v2/data-props/load-when-visible>`_

What Is Load When Visible?
--------------------------

The WhenVisible component triggers a partial reload when it scrolls into view.
Combine it with optional props to avoid sending data until it is needed.

Backend Usage
-------------

.. code-block:: python

   from typing import Any

   from litestar import get
   from litestar_vite.inertia import optional

   @get("/posts/{post_id}", component="Posts/Show")
   async def show_post(post_id: int) -> dict[str, Any]:
       return {
           "post": await Post.get(post_id),
           "comments": optional("comments", lambda: Comment.for_post(post_id)),
           "related": optional("related", lambda: Post.related(post_id)),
       }

Optional props are not included in the initial response or standard partial reloads.

Frontend Usage
--------------

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { WhenVisible, usePage } from "@inertiajs/react";

         export default function Post() {
           const { post, comments } = usePage().props;

           return (
             <article>
               <PostBody post={post} />

               <WhenVisible data="comments" fallback={<Spinner />}>
                 <Comments items={comments} />
               </WhenVisible>
             </article>
           );
         }

   .. tab-item:: Vue

      .. code-block:: text

         <script setup lang="ts">
         import { WhenVisible } from "@inertiajs/vue3";

         const props = defineProps<{ post: Post; comments?: Comment[] }>();
         </script>

         <template>
           <article>
             <PostBody :post="props.post" />

             <WhenVisible data="comments">
               <template #fallback><Spinner /></template>
               <Comments :items="props.comments" />
             </WhenVisible>
           </article>
         </template>

Visibility Controls
-------------------

Use WhenVisible options to control when reloads happen:

- ``buffer`` to start loading before the element is visible (acts as a threshold)
- ``always`` to reload every time it becomes visible

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         <WhenVisible data="comments" buffer={200} always>
           <Comments items={comments} />
         </WhenVisible>

   .. tab-item:: Vue

      .. code-block:: vue

         <WhenVisible data="comments" :buffer="200" always>
           <Comments :items="comments" />
         </WhenVisible>

See Also
--------

- :doc:`partial-reloads` - Partial reload behavior
- :doc:`once-props` - Cache-heavy props
- :doc:`infinite-scroll` - Build scroll-based loading

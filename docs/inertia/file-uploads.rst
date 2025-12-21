============
File Uploads
============

Upload files with Inertia form helpers and Litestar endpoints.

.. seealso::
   Official Inertia.js docs: `File Uploads <https://inertiajs.com/file-uploads>`_

How File Uploads Work
---------------------

Inertia will automatically submit ``FormData`` when a file is present. You can
also force ``FormData`` with ``forceFormData`` for mixed payloads.

Frontend Usage
--------------

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { useForm } from "@inertiajs/react";

         export default function AvatarForm() {
           const form = useForm({
             name: "",
             avatar: null as File | null,
           });

           function submit(e: React.FormEvent) {
             e.preventDefault();
             form.post("/profile", { forceFormData: true });
           }

           return (
             <form onSubmit={submit}>
               <input
                 type="file"
                 onChange={(e) => form.setData("avatar", e.target.files?.[0] ?? null)}
               />
               <button disabled={form.processing}>Upload</button>
             </form>
           );
         }

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import { useForm } from "@inertiajs/vue3";

         const form = useForm({
           name: "",
           avatar: null as File | null,
         });

         function submit() {
           form.post("/profile", { forceFormData: true });
         }
         </script>

         <template>
           <form @submit.prevent="submit">
             <input type="file" @change="(e) => (form.avatar = e.target.files?.[0] ?? null)" />
             <button :disabled="form.processing">Upload</button>
           </form>
         </template>

Upload Progress
---------------

Track progress using the ``progress`` field:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         {form.progress && <progress value={form.progress.percentage} max="100" />}

   .. tab-item:: Vue

      .. code-block:: vue

        <template>
          <progress v-if="form.progress" :value="form.progress.percentage" max="100" />
        </template>

Image Previews
--------------

Use ``URL.createObjectURL`` to preview images before upload:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         const previewUrl = form.data.avatar
           ? URL.createObjectURL(form.data.avatar)
           : null;

         {previewUrl && <img src={previewUrl} alt="Preview" />}

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import { computed } from "vue";

         const previewUrl = computed(() =>
           form.avatar ? URL.createObjectURL(form.avatar) : null
         );
         </script>

         <template>
           <img v-if="previewUrl" :src="previewUrl" alt="Preview" />
         </template>

Backend Usage
-------------

Handle files using Litestar's ``UploadFile``:

.. code-block:: python

   from litestar import post
   from litestar.datastructures import UploadFile
   from litestar.request import Request
   from litestar_vite.inertia import InertiaRedirect

   @post("/profile")
   async def update_profile(
       request: Request,
       avatar: UploadFile | None = None,
   ) -> InertiaRedirect:
       if avatar is not None:
           await avatar.save("./uploads/avatar.png")
       return InertiaRedirect(request, "/profile")

Multiple Files
--------------

.. code-block:: python

   @post("/documents")
   async def upload_documents(request: Request, files: list[UploadFile]) -> InertiaRedirect:
       for file in files:
           await file.save(f"./uploads/{file.filename}")
       return InertiaRedirect(request, "/documents")

See Also
--------

- :doc:`forms` - Form submissions
- :doc:`validation` - Validation errors for uploads
- :doc:`flash-data` - Success messaging

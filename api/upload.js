const { handleUpload } = require('@vercel/blob/client');

module.exports = async function (request, response) {
    const body = request.body;

    try {
        const jsonResponse = await handleUpload({
            body,
            request,
            onBeforeGenerateToken: async (pathname) => {
                // Here you can verify if the user is authorized to upload
                return {
                    allowedContentTypes: ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 'text/plain', 'text/markdown', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                    addRandomSuffix: true,
                    tokenPayload: JSON.stringify({
                        // optional payload
                    }),
                };
            },
            onUploadCompleted: async ({ blob, tokenPayload }) => {
                // This runs after the upload is completed on the client
                try {
                    console.log('blob uploaded', blob.url);
                } catch (error) {
                    throw new Error('Could not process upload');
                }
            },
        });

        return response.status(200).json(jsonResponse);
    } catch (error) {
        return response.status(400).json(
            { error: error.message }
        );
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const vocabList = document.getElementById('vocab-list');
    const wordInput = document.getElementById('word-input');
    const addWordBtn = document.getElementById('add-word-btn');
    const stagedWordsList = document.getElementById('staged-words-list');
    const generateBtn = document.getElementById('generate-btn');
    const downloadBtn = document.getElementById('download-btn');

    // Wait for authentication before accessing Firestore
    let vocabCollection = null;
    let unsubscribe = null; // Store the unsubscribe function for the snapshot listener

    auth.onAuthStateChanged(async (user) => {
        if (user && user.email === 'wzhybrid@gmail.com') {
            // Get Firestore instance
            const db = firebase.firestore();
            
            // Reference to the vocabulary collection
            vocabCollection = db.collection('vocabulary');
            
            // Set up real-time listener
            try {
                unsubscribe = vocabCollection.onSnapshot(snapshot => {
                    let vocabText = '';
                    snapshot.forEach(doc => {
                        const data = doc.data();
                        vocabText += `${data.simplified}\t${data.mandarin}<br><br>${data.cantonese}\n`;
                    });
                    vocabList.value = vocabText;
                }, error => {
                    console.error('Error in snapshot listener:', error);
                    vocabList.value = 'Error loading vocabulary list.';
                });
            } catch (error) {
                console.error('Error initializing collection:', error);
                vocabList.value = 'Error initializing vocabulary list.';
            }
        } else {
            // Clean up listener when user signs out
            if (unsubscribe) {
                unsubscribe();
                unsubscribe = null;
            }
            vocabCollection = null;
            vocabList.value = 'Please sign in with wzhybrid@gmail.com to access the vocabulary list.';
        }
    });

    // Function to fetch and display the vocabulary list
    const fetchVocab = async () => {
        if (!vocabCollection) {
            vocabList.value = 'Please sign in with wzhybrid@gmail.com to access the vocabulary list.';
            return;
        }
        try {
            const snapshot = await vocabCollection.get();
            let vocabText = '';
            snapshot.forEach(doc => {
                const data = doc.data();
                vocabText += `${data.simplified}\t${data.mandarin}<br><br>${data.cantonese}\n`;
            });
            vocabList.value = vocabText;
        } catch (error) {
            console.error('Error fetching vocabulary:', error);
            vocabList.value = 'Error loading vocabulary list.';
        }
    };

    // Function to add a word to the staged words list
    const addWord = () => {
        const word = wordInput.value.trim();
        if (word) {
            const li = document.createElement('li');
            li.textContent = word;
            stagedWordsList.appendChild(li);
            wordInput.value = '';
        }
    };

    // Function to send staged words to the backend to generate sentences and update Firestore
    const generateSentences = async () => {
        if (!vocabCollection) {
            alert('Please sign in with wzhybrid@gmail.com to generate sentences.');
            return;
        }
        const stagedWords = Array.from(stagedWordsList.children).map(li => li.textContent);
        
        generateBtn.disabled = true;
        let successCount = 0;
        let failCount = 0;
        
        for (const word of stagedWords) {
            try {
                const response = await fetch('https://us-central1-wz-data-catalog-demo.cloudfunctions.net/generate_sentences', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ word: word })
                });
                
                if (response.ok) {
                    successCount++;
                    // Remove the processed word from the list
                    const wordElement = Array.from(stagedWordsList.children).find(li => li.textContent === word);
                    if (wordElement) {
                        stagedWordsList.removeChild(wordElement);
                    }
                } else {
                    failCount++;
                    console.error(`Failed to generate sentences for word: ${word}`);
                }
                
                // Add a small delay between requests to avoid overwhelming the service
                await new Promise(resolve => setTimeout(resolve, 1000));
            } catch (error) {
                failCount++;
                console.error(`Error generating sentences for word: ${word}:`, error);
            }
        }
        
        generateBtn.disabled = false;
        
        if (failCount > 0) {
            alert(`Completed with ${successCount} successes and ${failCount} failures. Check console for details.`);
        }
    };

    // Function to download the vocab.txt file
    const downloadVocab = async () => {
        if (!vocabCollection) {
            alert('Please sign in with wzhybrid@gmail.com to download the vocabulary list.');
            return;
        }
        try {
            const snapshot = await vocabCollection.get();
            let vocabText = '';
            snapshot.forEach(doc => {
                const data = doc.data();
                if (data.simplified && data.mandarin) { // Only include if there's actual content
                    vocabText += `${data.simplified}\t${data.mandarin}<br><br>${data.cantonese}\n`;
                }
            });
    
            // Add Anki configuration headers
            const ankiHeaders = '#separator:tab\n#html:true\n';
            const blob = new Blob([ankiHeaders + vocabText], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'vocab.txt';
            document.body.appendChild(a); // Append the link to the body
            a.click();
            document.body.removeChild(a); // Remove the link from the body
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error downloading vocabulary:', error);
            alert('Error downloading vocabulary.');
        }
    };

    // Event listeners
    addWordBtn.addEventListener('click', addWord);
    generateBtn.addEventListener('click', generateSentences);
    downloadBtn.addEventListener('click', downloadVocab);
});
document.addEventListener('DOMContentLoaded', () => {
    const vocabList = document.getElementById('vocab-list');
    const wordInput = document.getElementById('word-input');
    const addWordBtn = document.getElementById('add-word-btn');
    const downloadBtn = document.getElementById('download-btn');

    // Wait for authentication before accessing Firestore
    let vocabCollection = null;
    let unsubscribe = null; // Store the unsubscribe function for the snapshot listener

    // Load sort preference from localStorage
    const sortPreference = document.querySelector('input[name="sort-order"]:checked');
    let sortOrder = localStorage.getItem('sortOrder') || 'top';
    document.querySelector(`input[name="sort-order"][value="${sortOrder}"]`).checked = true;

    // Update sort preference when radio buttons change
    document.querySelectorAll('input[name="sort-order"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            sortOrder = e.target.value;
            localStorage.setItem('sortOrder', sortOrder);
            // Refresh the display if we have data
            if (vocabCollection) {
                fetchVocab();
            }
        });
    });

    auth.onAuthStateChanged(async (user) => {
        if (user && user.email === 'wzhybrid@gmail.com') {
            // Get Firestore instance
            const db = firebase.firestore();
            
            // Reference to the vocabulary collection
            vocabCollection = db.collection('vocabulary');
            
            // Set up real-time listener
            try {
                unsubscribe = vocabCollection.onSnapshot(snapshot => {
                    // Convert snapshot to array for sorting
                    const entries = [];
                    snapshot.forEach(doc => {
                        // Log document details for debugging
                        console.log(`Document ${doc.id}:`, {
                            word: doc.data().simplified,
                            createTime: doc.createTime ? doc.createTime.toDate() : 'No createTime',
                            updateTime: doc.updateTime ? doc.updateTime.toDate() : 'No updateTime'
                        });
                        
                        const data = doc.data();
                        entries.push({
                            ...data,
                            id: doc.id,
                            timestamp: data.timestamp ? data.timestamp.toMillis() : Date.now()
                        });
                    });

                    // Sort entries based on timestamp
                    entries.sort((a, b) => {
                        return sortOrder === 'top' ? 
                            b.timestamp - a.timestamp : 
                            a.timestamp - b.timestamp;
                    });

                    // Log sorted entries for debugging
                    console.log('Sorted entries:', entries.map(entry => ({
                        id: entry.id,
                        word: entry.simplified,
                        timestamp: new Date(entry.timestamp)
                    })));

                    // Create text content
                    let vocabText = '';
                    entries.forEach(entry => {
                        vocabText += `${entry.simplified}\t${entry.mandarin}<br><br>${entry.cantonese}\n`;
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
            const entries = [];
            snapshot.forEach(doc => {
                const data = doc.data();
                entries.push({
                    ...data,
                    timestamp: data.timestamp ? data.timestamp.toMillis() : Date.now()
                });
            });

            // Sort entries based on timestamp
            entries.sort((a, b) => {
                return sortOrder === 'top' ? 
                    b.timestamp - a.timestamp : 
                    a.timestamp - b.timestamp;
            });

            // Create text content
            let vocabText = '';
            entries.forEach(entry => {
                vocabText += `${entry.simplified}\t${entry.mandarin}<br><br>${entry.cantonese}\n`;
            });
            vocabList.value = vocabText;
        } catch (error) {
            console.error('Error fetching vocabulary:', error);
            vocabList.value = 'Error loading vocabulary list.';
        }
    };

    // Function to add a word and generate sentences
    const addWord = async () => {
        const word = wordInput.value.trim();
        if (!word) return;
        
        if (!vocabCollection) {
            alert('Please sign in with wzhybrid@gmail.com to add words.');
            return;
        }

        // Disable input while processing
        addWordBtn.disabled = true;
        wordInput.disabled = true;

        try {
            const response = await fetch('https://us-central1-wz-data-catalog-demo.cloudfunctions.net/generate_sentences', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ word: word })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to generate sentences for word: ${word}`);
            }
            
            // Clear input on success
            wordInput.value = '';
            
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to process word. Check console for details.');
        } finally {
            // Re-enable input
            addWordBtn.disabled = false;
            wordInput.disabled = false;
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
            const entries = [];
            snapshot.forEach(doc => {
                const data = doc.data();
                if (data.simplified && data.mandarin) { // Only include if there's actual content
                    entries.push({
                        ...data,
                        timestamp: data.timestamp ? data.timestamp.toMillis() : Date.now()
                    });
                }
            });

            // Sort entries based on timestamp
            entries.sort((a, b) => {
                return sortOrder === 'top' ? 
                    b.timestamp - a.timestamp : 
                    a.timestamp - b.timestamp;
            });

            // Create text content
            let vocabText = '';
            entries.forEach(entry => {
                vocabText += `${entry.simplified}\t${entry.mandarin}<br><br>${entry.cantonese}\n`;
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
    downloadBtn.addEventListener('click', downloadVocab);
});

import { useState, useEffect } from 'react';
import { auth } from '../lib/firebase';
import { User, updateProfile, signOut } from 'firebase/auth';
import { Camera, LogOut } from 'lucide-react';

const HOST = import.meta.env.VITE_CHAT_HOST;

function ProfilePage() {
    const [user, setUser] = useState<User | null>(null);
    const [isHovered, setIsHovered] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    useEffect(() => {
        const unsubscribe = auth.onAuthStateChanged((user) => {
            setUser(user);
        });

        return () => unsubscribe();
    }, []);

    const getInitials = (name: string | null) => {
        if (!name) return '?';
        return name
            .split(' ')
            .filter(Boolean)
            .map(word => word[0].toUpperCase())
            .join('')
            .slice(0, 2);
    };

    const handlePhotoUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file || !user) return;

        if (file.size > 5 * 1024 * 1024) {
            alert('File is too large. Please upload an image smaller than 5MB.');
            return;
        }

        event.target.value = '';
        setIsUploading(true);

        try {
            const formData = new FormData();
            formData.append('file', file);
            const idToken = await user.getIdToken();

            const response = await fetch(`${HOST}/api/v1/users/profile/picture`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                },
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Failed to upload photo');
            }

            const data = await response.json();
            await updateProfile(auth.currentUser!, { photoURL: data.photo_url });
            setUser(auth.currentUser);

        } catch (error) {
            console.error('Error uploading photo:', error);
            alert('Failed to upload photo. Please try again.');
        } finally {
            setIsUploading(false);
        }
    };

    const handleLogout = async () => {
        try {
            await signOut(auth);
        } catch (error) {
            console.error('Error signing out:', error);
            alert('Failed to sign out. Please try again.');
        }
    };

    if (!user) {
        return <div className="flex items-center justify-center min-h-screen dark:bg-gray-900">Loading...</div>;
    }

    return (
        <div className="max-w-3xl mx-auto p-8">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
                <div className="text-center mb-8">
                    <div
                        className={`relative w-40 h-40 mx-auto mb-4 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-700 transition-transform duration-300 ${
                            isHovered ? 'scale-110' : ''
                        }`}
                        onMouseEnter={() => setIsHovered(true)}
                        onMouseLeave={() => setIsHovered(false)}
                    >
                        {user.photoURL ? (
                            <img
                                src={user.photoURL}
                                alt="Profile"
                                className="w-full h-full object-cover"
                            />
                        ) : (
                            <div className="w-full h-full flex items-center justify-center text-4xl font-semibold text-gray-600 dark:text-gray-300 bg-gray-200 dark:bg-gray-700">
                                {getInitials(user.displayName)}
                            </div>
                        )}
                        <label className={`absolute bottom-0 left-0 right-0 bg-black/70 text-white p-3 cursor-pointer flex items-center justify-center transition-transform duration-300 ${
                            isHovered ? 'translate-y-0' : 'translate-y-full'
                        }`}>
                            <Camera size={24} />
                            <input
                                type="file"
                                accept="image/*"
                                onChange={handlePhotoUpload}
                                className="hidden"
                                disabled={isUploading}
                            />
                        </label>
                    </div>
                    <h1 className="text-3xl font-bold text-gray-800 dark:text-white mb-2">
                        {user.displayName || 'User'}
                    </h1>
                    <p className="text-gray-600 dark:text-gray-300">{user.email}</p>
                </div>

                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-6">
                    <div className="mb-6">
                        <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">Account Information</h2>
                        <div className="space-y-4">
                            <div className="flex border-b border-gray-200 dark:border-gray-600 pb-4">
                                {/* <span className="font-medium text-gray-600 dark:text-gray-300 w-40">Email:</span>
                                <span className="text-gray-800 dark:text-white">{user.email}</span> */}
                            </div>
                            <div className="flex border-b border-gray-200 dark:border-gray-600 pb-4">
                                <span className="font-medium text-gray-600 dark:text-gray-300 w-40">Account Created:</span>
                                <span className="text-gray-800 dark:text-white">
                                    {user.metadata.creationTime ? new Date(user.metadata.creationTime).toLocaleDateString() : 'N/A'}
                                </span>
                            </div>
                            <div className="flex pb-4">
                                <span className="font-medium text-gray-600 dark:text-gray-300 w-40">Last Sign In:</span>
                                <span className="text-gray-800 dark:text-white">
                                    {user.metadata.lastSignInTime ? new Date(user.metadata.lastSignInTime).toLocaleDateString() : 'N/A'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <button 
                    onClick={handleLogout}
                    className="mt-8 flex items-center gap-2 px-6 py-2.5 text-gray-600 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg font-medium hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-gray-400 dark:hover:border-gray-500 transition-all duration-200 active:scale-95"
                >
                    <LogOut size={18} />
                    Sign Out
                </button>
            </div>
        </div>
    );
}

export default ProfilePage;
